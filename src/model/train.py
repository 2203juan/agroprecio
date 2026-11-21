"""Entrenamiento, evaluación contra baselines y registro de versiones del modelo."""
import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.model.metrics import classification_metrics, simulated_saving
from src.transform.gold_transformations import FEATURES, classify


def build_model(random_state):
    prep = ColumnTransformer([
        ("producto", OneHotEncoder(handle_unknown="ignore"), ["producto"]),
        ("num", "passthrough", FEATURES),
    ])
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=5,
        class_weight="balanced", random_state=random_state,
    )
    return Pipeline([("prep", prep), ("clf", clf)])


def split_by_time(gold, test_weeks):
    data = gold.dropna(subset=FEATURES + ["clase"])
    weeks = sorted(data["semana_inicio"].unique())
    cut = weeks[-test_weeks]
    return data[data["semana_inicio"] < cut], data[data["semana_inicio"] >= cut]


def evaluate(test, pred, proba=None):
    return {
        **classification_metrics(test["clase"], pred, proba),
        "ahorro_simulado": round(simulated_saving(test, pred), 4),
    }


def train(gold, cfg, logger):
    mcfg = cfg["model"]
    train_df, test_df = split_by_time(gold, mcfg["test_weeks"])
    logger.info("Entrenamiento: %s filas, prueba: %s filas", len(train_df), len(test_df))

    model = build_model(mcfg["random_state"])
    model.fit(train_df[["producto"] + FEATURES], train_df["clase"])
    pred = model.predict(test_df[["producto"] + FEATURES])

    # Baseline de persistencia: lo que pasó la semana pasada vuelve a pasar
    baseline = test_df["cambio_1s"].apply(classify, threshold=mcfg["threshold"])

    metrics = {
        "modelo": evaluate(test_df, pred, model.predict_proba(test_df[["producto"] + FEATURES])),
        "baseline_persistencia": evaluate(test_df, baseline),
        "baseline_estable": evaluate(test_df, ["estable"] * len(test_df)),
    }
    beats_baseline = metrics["modelo"]["f1_macro"] > metrics["baseline_persistencia"]["f1_macro"]
    good_enough = metrics["modelo"]["accuracy"] >= cfg["monitoring"]["min_accuracy"]

    version = datetime.now().strftime("v%Y%m%d_%H%M%S")
    models_dir = Path(cfg["paths"]["models"])
    models_dir.mkdir(exist_ok=True)
    joblib.dump(model, models_dir / f"{version}.joblib")

    entry = {
        "version": version,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "estado": "produccion" if beats_baseline and good_enough else "rechazado",
        "datos": {
            "filas_entrenamiento": len(train_df),
            "filas_prueba": len(test_df),
            "desde": str(train_df["semana_inicio"].min().date()),
            "hasta": str(test_df["semana_inicio"].max().date()),
        },
        "features": FEATURES,
        "parametros": model.named_steps["clf"].get_params(),
        "metricas": metrics,
    }
    register(entry, models_dir)
    logger.info("Modelo %s: %s | %s", version, entry["estado"], metrics["modelo"])

    test_out = test_df[["semana_inicio", "producto", "precio", "clase"]].copy()
    test_out["prediccion"] = pred
    return entry, test_out


def register(entry, models_dir):
    path = Path(models_dir) / "registry.json"
    registry = json.loads(path.read_text()) if path.exists() else []
    if entry["estado"] == "produccion":
        for old in registry:
            if old["estado"] == "produccion":
                old["estado"] = "archivado"
    registry.append(entry)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False, default=str))


def load_production(models_dir):
    path = Path(models_dir) / "registry.json"
    if not path.exists():
        return None, None
    registry = json.loads(path.read_text())
    prod = [r for r in registry if r["estado"] == "produccion"]
    if not prod:
        return None, None
    entry = prod[-1]
    return joblib.load(Path(models_dir) / f"{entry['version']}.joblib"), entry
