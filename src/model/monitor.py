"""Monitoreo: qué tan bien le fue al modelo en producción y si los datos cambiaron."""
from datetime import datetime

import pandas as pd


def score_predictions(log, gold):
    """Cruza las predicciones guardadas con lo que realmente pasó."""
    real = gold[["semana_inicio", "producto", "clase"]].dropna()
    real["semana_inicio"] = pd.to_datetime(real["semana_inicio"])
    log = log.copy()
    log["semana_inicio"] = pd.to_datetime(log["semana_inicio"])
    scored = log.merge(real, on=["semana_inicio", "producto"], how="inner")
    scored["acierto"] = scored["prediccion"] == scored["clase"]
    return scored


def weekly_accuracy(scored):
    """reales: cuántas se hicieron antes de conocer el resultado (las demás son backtest)."""
    return (scored.groupby("semana_inicio", as_index=False)
            .agg(predicciones=("acierto", "size"), accuracy=("acierto", "mean"),
                 reales=("confianza", "count"))
            .sort_values("semana_inicio"))


def data_drift(gold, zscore):
    """Marca productos cuyo cambio de la última semana es atípico frente a su historia."""
    rows = []
    for product, g in gold.dropna(subset=["cambio_1s"]).groupby("producto"):
        hist, last = g.iloc[:-1], g.iloc[-1]
        std = hist["cambio_1s"].std()
        z = 0 if not std else (last["cambio_1s"] - hist["cambio_1s"].mean()) / std
        rows.append({
            "producto": product,
            "semana_inicio": last["semana_inicio"],
            "cambio_1s": round(last["cambio_1s"], 4),
            "zscore": round(z, 2),
            "drift": abs(z) > zscore,
        })
    return pd.DataFrame(rows)


def real_accuracy(scored):
    """Acierto solo de las predicciones hechas antes de conocer el resultado.
    Las del backtest se guardan sin confianza y no cuentan."""
    real = scored[scored["confianza"].notna()]
    return len(real), (round(float(real["acierto"].mean()), 4) if len(real) else None)


def summary(scored, drift, cfg, entry):
    recent = scored.sort_values("semana_inicio").groupby("producto").tail(8)
    acc = float(recent["acierto"].mean()) if len(recent) else None
    drift_share = float(drift["drift"].mean()) if len(drift) else 0.0
    needs_retrain = (acc is not None and acc < cfg["monitoring"]["min_accuracy"]) or drift_share > 0.3
    n_real, acc_real = real_accuracy(scored)
    return pd.DataFrame([{
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo_version": entry["version"],
        "accuracy_ultimas_8_semanas": None if acc is None else round(acc, 4),
        "productos_con_drift": int(drift["drift"].sum()),
        "requiere_reentrenar": bool(needs_retrain),
        "predicciones_reales": n_real,
        "accuracy_real": acc_real,
    }])


def product_accuracy(scored, weeks=8):
    """Aciertos por producto en sus últimas semanas evaluadas (ej.: 5 de 8)."""
    recent = scored.sort_values("semana_inicio").groupby("producto").tail(weeks)
    return (recent.groupby("producto", as_index=False)
            .agg(aciertos=("acierto", "sum"), evaluadas=("acierto", "size")))
