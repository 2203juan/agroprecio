"""Pipeline de AgroPrecio.

    python main.py                     # todo: descarga, limpia, entrena si hace falta, predice
    python main.py --sin-descarga      # usa solo lo que ya está en data/bronze
    python main.py --reentrenar        # fuerza un modelo nuevo
    python main.py --etapa silver      # una sola etapa (así lo corre Airflow)

Las etapas se comunican por los archivos de cada capa y por la base, no por memoria,
para que cada una se pueda repetir sola.
"""
import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.extract.extract_diario import download_daily, extract_daily
from src.extract.extract_excel import download_bulletins, extract_all
from src.llm.boletin import generate_bulletin
from src.load.load_database import read_table, save_table
from src.model import monitor, tracking
from src.model.predict import add_backtest, add_to_log, expected_range, predict_latest
from src.model.train import ALGORITHM, load_production, train, training_rows, usable_features
from src.quality import CRITICAL, check_gold, check_silver
from src.transform.clean_excel import clean_bulletins
from src.transform.diario import clean_daily
from src.transform.gold_transformations import build_panel, gold_from_panel


def get_logger(log_dir):
    Path(log_dir).mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(Path(log_dir) / "pipeline.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )
    return logging.getLogger("agroprecio")


def silver_path(cfg):
    return Path(cfg["paths"]["silver"]) / "precios.parquet"


def daily_path(cfg):
    return Path(cfg["paths"]["silver"]) / "diario.parquet"


def gold_path(cfg):
    return Path(cfg["paths"]["gold"]) / "features.parquet"


def panel_path(cfg):
    return Path(cfg["paths"]["gold"]) / "entrenamiento.parquet"


def stage_descargar(cfg, log):
    download_bulletins(cfg, log)
    download_daily(cfg, log)


def stage_silver(cfg, log):
    silver = clean_bulletins(extract_all(cfg, log))
    silver.to_parquet(silver_path(cfg), index=False)
    log.info("Silver: %s filas", len(silver))
    raw_daily = extract_daily(cfg)
    if raw_daily is not None:
        daily = clean_daily(raw_daily)
        daily.to_parquet(daily_path(cfg), index=False)
        log.info("Silver diario: %s filas hasta el %s", len(daily), daily["fecha"].max().date())


def stage_gold(cfg, log):
    daily = pd.read_parquet(daily_path(cfg)) if daily_path(cfg).exists() else None
    panel = build_panel(pd.read_parquet(silver_path(cfg)), cfg["market"], cfg["products"],
                        cfg["model"]["threshold"], daily)
    gold = gold_from_panel(panel, cfg["market"])
    panel.to_parquet(panel_path(cfg), index=False)
    gold.to_parquet(gold_path(cfg), index=False)
    log.info("Gold: %s filas de %s, %s para entrenar", len(gold), cfg["market"], len(panel))


def stage_calidad(cfg, log):
    """Valida silver y gold. Solo publica las tablas si pasan las reglas críticas."""
    db = cfg["paths"]["database"]
    silver, gold = pd.read_parquet(silver_path(cfg)), pd.read_parquet(gold_path(cfg))
    quality = pd.concat([check_silver(silver), check_gold(gold, cfg["products"])], ignore_index=True)
    quality["fecha"] = datetime.now().isoformat(timespec="seconds")  # una sola fecha por corrida
    save_table(quality, "calidad_datos", db, mode="append")

    failed = quality.loc[~quality["ok"], "regla"].tolist()
    if failed:
        log.warning("Reglas de calidad que fallaron: %s", failed)
    if set(failed) & CRITICAL:
        raise SystemExit("Los datos no pasaron las reglas críticas de calidad")

    save_table(silver[silver["mercado"].str.startswith("Cali")], "precios_cali", db)
    save_table(gold, "features", db)
    log.info("Calidad: %s de %s reglas pasan", len(quality) - len(failed), len(quality))


def stage_modelo(cfg, log, retrain=False):
    paths, db = cfg["paths"], cfg["paths"]["database"]
    gold = pd.read_parquet(gold_path(cfg))
    model, entry = load_production(paths["models"])
    last_monitor = read_table("monitoreo", db)
    # Solo vale la pena reentrenar si el monitoreo lo pidió y llegaron semanas nuevas
    asked_retrain = (
        entry is not None and not last_monitor.empty
        and bool(last_monitor["requiere_reentrenar"].iloc[-1])
        and str(gold.dropna(subset=["clase"])["semana_inicio"].max().date()) > entry["datos"]["hasta"]
    )
    panel = pd.read_parquet(panel_path(cfg))
    # O si el código trae otra receta: otro algoritmo o variables que el modelo no conoce
    new_recipe = entry is not None and (
        entry["parametros"].get("algoritmo") != ALGORITHM
        or set(usable_features(training_rows(panel))) != set(entry["features"]))
    if new_recipe:
        log.info("La receta del modelo cambió frente a %s: se reentrena", entry["version"])
    if retrain or model is None or asked_retrain or new_recipe:
        entry, backtest = train(gold, panel, cfg, log)
        if entry["estado"] == "produccion":
            backtest["modelo_version"] = entry["version"]
            backtest["confianza"] = None
            backtest["fecha_prediccion"] = entry["fecha"]
            save_table(add_backtest(read_table("predicciones", db), backtest), "predicciones", db)
    else:
        log.info("No hace falta reentrenar: sigue %s", entry["version"])
    tracking.sync_registry(cfg, log)
    if load_production(paths["models"])[0] is None:
        raise SystemExit("No hay un modelo en producción que supere el baseline")


def stage_prediccion(cfg, log):
    paths, db = cfg["paths"], cfg["paths"]["database"]
    gold = pd.read_parquet(gold_path(cfg))
    model, entry = load_production(paths["models"])
    if model is None:
        raise SystemExit("No hay un modelo en producción que supere el baseline")

    alerts = expected_range(gold, predict_latest(gold, model, entry))
    save_table(add_to_log(read_table("predicciones", db), alerts), "predicciones", db)

    scored = monitor.score_predictions(read_table("predicciones", db), gold)
    drift = monitor.data_drift(gold, cfg["monitoring"]["drift_zscore"])
    save_table(monitor.weekly_accuracy(scored), "accuracy_semanal", db)
    save_table(drift, "drift", db)
    # Cada alerta lleva cuántas veces acertó el modelo con ese producto
    alerts = alerts.merge(monitor.product_accuracy(scored), on="producto", how="left")
    save_table(alerts, "alertas", db)
    status = monitor.summary(scored, drift, cfg, entry)
    save_table(status, "monitoreo", db, mode="append")
    log.info("Monitoreo: %s", status.iloc[0].to_dict())


def stage_boletin(cfg, log):
    db = cfg["paths"]["database"]
    bulletin = generate_bulletin(read_table("alertas", db), cfg, log)
    save_table(pd.DataFrame([bulletin]), "boletines", db, mode="append")
    log.info("Boletín generado con %s", bulletin["fuente"])


STAGES = {
    "descargar": stage_descargar,
    "silver": stage_silver,
    "gold": stage_gold,
    "calidad": stage_calidad,
    "modelo": stage_modelo,
    "prediccion": stage_prediccion,
    "boletin": stage_boletin,
}


def run(cfg, download=True, retrain=False):
    log = get_logger(cfg["paths"]["logs"])
    log.info("=== Inicio del pipeline ===")
    for name, stage in STAGES.items():
        if name == "descargar" and not download:
            continue
        if name == "modelo":
            stage(cfg, log, retrain)
        else:
            stage(cfg, log)
    log.info("=== Fin del pipeline ===")


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline AgroPrecio")
    parser.add_argument("--sin-descarga", action="store_true")
    parser.add_argument("--reentrenar", action="store_true")
    parser.add_argument("--etapa", choices=STAGES, help="Corre una sola etapa")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if args.etapa == "modelo":
        stage_modelo(config, get_logger(config["paths"]["logs"]), args.reentrenar)
    elif args.etapa:
        STAGES[args.etapa](config, get_logger(config["paths"]["logs"]))
    else:
        run(config, download=not args.sin_descarga, retrain=args.reentrenar)
