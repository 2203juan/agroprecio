"""Pipeline de AgroPrecio.

    python main.py                  # todo: descarga, limpia, entrena si hace falta, predice
    python main.py --sin-descarga   # usa solo lo que ya está en data/bronze
    python main.py --reentrenar     # fuerza un modelo nuevo
"""
import argparse
import logging
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.extract.extract_excel import download_bulletins, extract_all
from src.llm.boletin import generate_bulletin
from src.load.load_database import read_table, save_table
from src.model import monitor
from src.model.predict import add_to_log, predict_latest
from src.model.train import load_production, train
from src.quality import check_gold, check_silver
from src.transform.clean_excel import clean_prices
from src.transform.gold_transformations import build_gold


def get_logger(log_dir):
    Path(log_dir).mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(Path(log_dir) / "pipeline.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )
    return logging.getLogger("agroprecio")


def run(cfg, download=True, retrain=False):
    paths = cfg["paths"]
    db = paths["database"]
    log = get_logger(paths["logs"])
    log.info("=== Inicio del pipeline ===")

    # Bronze
    if download:
        download_bulletins(cfg, log)
    raw = extract_all(cfg, log)

    # Silver
    silver = clean_prices(raw)
    silver.to_parquet(Path(paths["silver"]) / "precios.parquet", index=False)
    quality = check_silver(silver)

    # Gold
    gold = build_gold(silver, cfg["market"], cfg["products"], cfg["model"]["threshold"])
    gold.to_parquet(Path(paths["gold"]) / "features.parquet", index=False)
    quality = pd.concat([quality, check_gold(gold, cfg["products"])], ignore_index=True)
    save_table(quality, "calidad_datos", db, mode="append")

    failed = quality[~quality["ok"]]
    if not failed.empty:
        log.warning("Reglas de calidad que fallaron: %s", failed["regla"].tolist())
    if "sin_nulos_en_llaves" in failed["regla"].values or "precios_positivos" in failed["regla"].values:
        raise SystemExit("Los datos no pasaron las reglas críticas de calidad")

    save_table(silver[silver["mercado"].str.startswith("Cali")], "precios_cali", db)
    save_table(gold, "features", db)
    log.info("Silver: %s filas | Gold: %s filas", len(silver), len(gold))

    # Modelo
    model, entry = load_production(paths["models"])
    last_monitor = read_table("monitoreo", db)
    # Solo vale la pena reentrenar si el monitoreo lo pidió y llegaron semanas nuevas
    asked_retrain = (
        entry is not None and not last_monitor.empty
        and bool(last_monitor["requiere_reentrenar"].iloc[-1])
        and str(gold.dropna(subset=["clase"])["semana_inicio"].max().date()) > entry["datos"]["hasta"]
    )
    if retrain or model is None or asked_retrain:
        entry, backtest = train(gold, cfg, log)
        if entry["estado"] == "produccion":
            backtest["modelo_version"] = entry["version"]
            backtest["confianza"] = None
            backtest["fecha_prediccion"] = entry["fecha"]
            pred_log = add_to_log(read_table("predicciones", db), backtest)
            save_table(pred_log, "predicciones", db)
        model, entry = load_production(paths["models"])
        if model is None:
            raise SystemExit("No hay un modelo en producción que supere el baseline")

    # Predicción de la semana
    alerts = predict_latest(gold, model, entry)
    save_table(alerts, "alertas", db)
    save_table(add_to_log(read_table("predicciones", db), alerts), "predicciones", db)

    # Monitoreo
    scored = monitor.score_predictions(read_table("predicciones", db), gold)
    drift = monitor.data_drift(gold, cfg["monitoring"]["drift_zscore"])
    save_table(monitor.weekly_accuracy(scored), "accuracy_semanal", db)
    save_table(drift, "drift", db)
    status = monitor.summary(scored, drift, cfg, entry)
    save_table(status, "monitoreo", db, mode="append")
    log.info("Monitoreo: %s", status.iloc[0].to_dict())

    # Boletín con LLM
    bulletin = generate_bulletin(alerts, cfg, log)
    save_table(pd.DataFrame([bulletin]), "boletines", db, mode="append")
    log.info("Boletín generado con %s", bulletin["fuente"])
    log.info("=== Fin del pipeline ===")


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline AgroPrecio")
    parser.add_argument("--sin-descarga", action="store_true")
    parser.add_argument("--reentrenar", action="store_true")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    run(config, download=not args.sin_descarga, retrain=args.reentrenar)
