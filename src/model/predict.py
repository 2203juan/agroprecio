"""Predicciones de la última semana y alertas de compra."""
from datetime import datetime

import pandas as pd

from src.transform.gold_transformations import BASE_FEATURES

ACTIONS = {
    "sube": "Compra esta semana",
    "baja": "Espera a la próxima semana",
    "estable": "Compra normal",
}


def recommend(prediction, confidence, min_confidence):
    """Lo que se le dice al restaurante: la clase del modelo solo si la confianza alcanza.
    Con poca confianza el modelo acierta menos de la mitad de las veces, así que calla."""
    clear = pd.Series(confidence, index=prediction.index) >= min_confidence
    return prediction.where(clear, "estable"), clear.map({True: "clara", False: "debil"})


def predict_latest(gold, model, entry, min_confidence=0.0):
    latest = gold.dropna(subset=BASE_FEATURES).sort_values("semana_inicio").groupby("producto").tail(1)
    # Cada versión guarda las variables con las que se entrenó
    X = latest[["producto"] + entry["features"]]
    proba = model.predict_proba(X)

    out = latest[["semana_inicio", "producto", "grupo", "precio", "cambio_1s", "precio_nacional"]].copy()
    out["prediccion"] = model.predict(X)
    out["confianza"] = proba.max(axis=1).round(3)
    out["recomendacion"], out["senal"] = recommend(out["prediccion"], out["confianza"], min_confidence)
    out["accion"] = out["recomendacion"].map(ACTIONS)
    out["modelo_version"] = entry["version"]
    out["fecha_prediccion"] = datetime.now().isoformat(timespec="seconds")
    # Primero lo que conviene comprar ya
    order = out["recomendacion"].map({"sube": 0, "baja": 1, "estable": 2})
    return out.assign(_orden=order).sort_values(["_orden", "confianza"], ascending=[True, False]) \
              .drop(columns="_orden").reset_index(drop=True)


def add_to_log(log, new):
    """Historial de predicciones: una por producto y semana (la más reciente gana)."""
    keep = ["semana_inicio", "producto", "precio", "prediccion", "recomendacion", "confianza",
            "modelo_version", "fecha_prediccion"]
    if "recomendacion" not in new:
        new = new.assign(recomendacion=new["prediccion"])
    both = pd.concat([log, new[keep]], ignore_index=True) if not log.empty else new[keep]
    both["semana_inicio"] = pd.to_datetime(both["semana_inicio"])
    return both.drop_duplicates(["semana_inicio", "producto"], keep="last")


def add_backtest(log, backtest):
    """Agrega el backtest sin pisar las predicciones reales (las que tienen confianza),
    que se hicieron antes de conocer el resultado."""
    if not log.empty:
        real = log[log["confianza"].notna()]
        keys = set(zip(pd.to_datetime(real["semana_inicio"]), real["producto"]))
        repeated = [(w, p) in keys for w, p in zip(pd.to_datetime(backtest["semana_inicio"]), backtest["producto"])]
        backtest = backtest[[not r for r in repeated]]
    return add_to_log(log, backtest)


def expected_range(gold, alerts):
    """Rango de precio para la próxima semana: lo que pasó con ese producto
    las veces que tuvo la misma clase (percentiles 25 y 75 del cambio)."""
    hist = gold.dropna(subset=["clase"])
    q = (hist.groupby(["producto", "clase"])["cambio_siguiente"]
         .quantile([0.25, 0.75]).unstack().reset_index()
         .rename(columns={"clase": "prediccion", 0.25: "q25", 0.75: "q75"}))
    out = alerts.merge(q, on=["producto", "prediccion"], how="left")
    out["precio_min_esperado"] = (out["precio"] * (1 + out["q25"].fillna(0))).round()
    out["precio_max_esperado"] = (out["precio"] * (1 + out["q75"].fillna(0))).round()
    return out.drop(columns=["q25", "q75"])
