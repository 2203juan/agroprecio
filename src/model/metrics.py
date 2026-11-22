"""Métricas de clasificación de los modelos y de los baselines."""
import pandas as pd
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, cohen_kappa_score, confusion_matrix, f1_score,
    log_loss, matthews_corrcoef, precision_recall_fscore_support, precision_score, recall_score,
    roc_auc_score,
)

from src.transform.gold_transformations import BASE_FEATURES, classify

CLASSES = ["baja", "estable", "sube"]  # mismo orden que model.classes_


def classification_metrics(y_true, y_pred, proba=None):
    """Las métricas más usadas. log_loss y roc_auc solo si hay probabilidades."""
    m = {
        "n": len(y_true),
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", labels=CLASSES, zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", labels=CLASSES, zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", labels=CLASSES, zero_division=0),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted", labels=CLASSES, zero_division=0),
        "cohen_kappa": cohen_kappa_score(y_true, y_pred),
        "mcc": matthews_corrcoef(y_true, y_pred),
        "log_loss": None,
        "roc_auc_ovr": None,
    }
    if proba is not None:
        m["log_loss"] = log_loss(y_true, proba, labels=CLASSES)
        m["roc_auc_ovr"] = roc_auc_score(y_true, proba, multi_class="ovr", labels=CLASSES)
    return {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in m.items()}


def per_class(y_true, y_pred):
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, zero_division=0)
    return pd.DataFrame({"clase": CLASSES, "precision": p.round(4), "recall": r.round(4),
                         "f1": f.round(4), "soporte": s})


def confusion(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    return {"filas_real_columnas_prediccion": CLASSES, "matriz": cm.tolist()}


def holdout(gold, hasta, test_weeks):
    """Las mismas semanas de prueba que usó el modelo al entrenarse."""
    data = gold.dropna(subset=BASE_FEATURES + ["clase"])
    data = data[data["semana_inicio"] <= pd.Timestamp(hasta)]
    weeks = sorted(data["semana_inicio"].unique())[-test_weeks:]
    return data[data["semana_inicio"].isin(weeks)]


def simulated_saving(test, pred):
    """Ahorro si el restaurante compra esta semana cuando el modelo dice 'sube'
    y, si no, compra la semana siguiente como de costumbre."""
    t = test.assign(pred=pred)
    paid_normal = t["precio_siguiente"].sum()
    paid_model = t["precio_siguiente"].where(t["pred"] != "sube", t["precio"]).sum()
    return float(1 - paid_model / paid_normal)


def evaluate_version(model, entry, gold, cfg):
    """Re-evalúa una versión guardada y los dos baselines sobre su periodo de prueba."""
    test = holdout(gold, entry["datos"]["hasta"], cfg["model"]["test_weeks"])
    X, y = test[["producto"] + entry["features"]], test["clase"]
    pred = model.predict(X)
    candidates = {
        "modelo": (pred, model.predict_proba(X)),
        "baseline_persistencia": (test["cambio_1s"].apply(classify, threshold=cfg["model"]["threshold"]), None),
        "baseline_estable": (["estable"] * len(test), None),
        "baseline_comprar_todo": (["sube"] * len(test), None),
    }
    rows = []
    for name, (p, proba) in candidates.items():
        rows.append({
            "version": entry["version"], "estado": entry["estado"], "evaluado": name,
            "prueba_desde": str(test["semana_inicio"].min().date()),
            "prueba_hasta": str(test["semana_inicio"].max().date()),
            **classification_metrics(y, p, proba),
            "ahorro_simulado": round(simulated_saving(test, p), 4),
        })
    return rows, per_class(y, pred), confusion(y, pred)
