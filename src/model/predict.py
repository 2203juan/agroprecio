"""Predicciones de la última semana y alertas de compra."""
from datetime import datetime

import pandas as pd

from src.transform.gold_transformations import FEATURES

ACTIONS = {
    "sube": "Compra esta semana",
    "baja": "Espera a la próxima semana",
    "estable": "Compra normal",
}


def predict_latest(gold, model, entry):
    latest = gold.dropna(subset=FEATURES).sort_values("semana_inicio").groupby("producto").tail(1)
    X = latest[["producto"] + FEATURES]
    proba = model.predict_proba(X)

    out = latest[["semana_inicio", "producto", "grupo", "precio", "cambio_1s", "precio_nacional"]].copy()
    out["prediccion"] = model.predict(X)
    out["confianza"] = proba.max(axis=1).round(3)
    out["accion"] = out["prediccion"].map(ACTIONS)
    out["modelo_version"] = entry["version"]
    out["fecha_prediccion"] = datetime.now().isoformat(timespec="seconds")
    return out.sort_values(["prediccion", "confianza"], ascending=[True, False]).reset_index(drop=True)


def add_to_log(log, new):
    """Historial de predicciones: una por producto y semana (la más reciente gana)."""
    keep = ["semana_inicio", "producto", "precio", "prediccion", "confianza", "modelo_version", "fecha_prediccion"]
    both = pd.concat([log, new[keep]], ignore_index=True) if not log.empty else new[keep]
    both["semana_inicio"] = pd.to_datetime(both["semana_inicio"])
    return both.drop_duplicates(["semana_inicio", "producto"], keep="last")
