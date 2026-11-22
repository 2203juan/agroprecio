import numpy as np
import pandas as pd

from src.model.metrics import CLASSES, classification_metrics, confusion, per_class, holdout
from src.model.train import build_model, usable_features
from src.transform.gold_transformations import BASE_FEATURES, build_gold
from tests.conftest import PRODUCTS


def test_perfect_prediction():
    y = ["sube", "baja", "estable", "sube"]
    m = classification_metrics(y, y)
    assert m["accuracy"] == 1 and m["f1_macro"] == 1 and m["cohen_kappa"] == 1
    assert m["log_loss"] is None and m["roc_auc_ovr"] is None


def test_probability_metrics():
    y = ["baja", "estable", "sube"]
    proba = np.eye(3) * 0.8 + 0.2 / 3  # columnas en el orden de CLASSES
    m = classification_metrics(y, y, proba)
    assert m["roc_auc_ovr"] == 1
    assert 0 < m["log_loss"] < 1


def test_per_class_and_confusion():
    y_true = ["sube", "sube", "baja", "estable"]
    y_pred = ["sube", "baja", "baja", "estable"]
    pc = per_class(y_true, y_pred).set_index("clase")
    assert pc.loc["sube", "recall"] == 0.5 and pc.loc["sube", "soporte"] == 2
    cm = confusion(y_true, y_pred)["matriz"]
    assert cm[CLASSES.index("sube")][CLASSES.index("baja")] == 1


def test_holdout_uses_last_weeks_up_to_cut(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    hasta = gold["semana_inicio"].sort_values().unique()[-3]
    test = holdout(gold, hasta, 4)
    assert test["semana_inicio"].nunique() == 4
    assert test["semana_inicio"].max() == hasta


def test_model_probabilities_follow_class_order(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03).dropna(subset=BASE_FEATURES + ["clase"])
    features = usable_features(gold)
    model = build_model(42, features).fit(gold[["producto"] + features], gold["clase"])
    assert list(model.classes_) == sorted(gold["clase"].unique())
    assert set(model.classes_) <= set(CLASSES)
