"""Compara variantes del modelo con validación hacia adelante en el tiempo.

    python -m src.model.experiments

Usa cinco bloques de 14 semanas, todos anteriores a las 20 semanas de prueba, que aquí no se
tocan. Cada bloque se predice con un modelo entrenado solo con semanas anteriores.
Guarda la tabla en docs/experimentos.csv y, si hay servidor, en MLflow.
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import QuantileTransformer

from src.model import tracking
from src.model.metrics import simulated_saving
from src.model.train import BOOSTING, TREES, build_model, evaluable, preprocess
from src.transform.gold_transformations import BASE_FEATURES, FEATURES, classify

BLOCKS, BLOCK_WEEKS = 5, 14


def blocks(gold, test_weeks):
    weeks = sorted(evaluable(gold)["semana_inicio"].unique())[:-test_weeks]
    end = len(weeks)
    return [weeks[end - BLOCK_WEEKS * (i + 1):end - BLOCK_WEEKS * i] for i in range(BLOCKS)][::-1]


def impute(model):
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), model)


def candidates(seed):
    forest = lambda: impute(RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=5, class_weight="balanced", random_state=seed, n_jobs=-1))
    trees = lambda: impute(ExtraTreesClassifier(**TREES, class_weight="balanced", random_state=seed, n_jobs=-1))
    boosting = lambda: HistGradientBoostingClassifier(**BOOSTING, class_weight="balanced", random_state=seed)
    logistic = lambda: make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        QuantileTransformer(output_distribution="normal", n_quantiles=200, random_state=seed),
        LogisticRegression(C=0.05, max_iter=600, class_weight="balanced"))

    def pipe(make, features):
        return lambda: Pipeline([("prep", preprocess(features)), ("clf", make())])

    return [  # nombre, variables, ¿solo Cavasa?, modelo
        ("Random Forest, variables básicas (v0.5)", BASE_FEATURES, True, pipe(forest, BASE_FEATURES)),
        ("Random Forest, todas las variables", FEATURES, True, pipe(forest, FEATURES)),
        ("ExtraTrees, todas las variables", FEATURES, True, pipe(trees, FEATURES)),
        ("Regresión logística, todas las variables", FEATURES, True, pipe(logistic, FEATURES)),
        ("HistGradientBoosting, todas las variables", FEATURES, True, pipe(boosting, FEATURES)),
        ("Random Forest, todas, mercados de Cali", FEATURES, False, pipe(forest, FEATURES)),
        ("ExtraTrees, todas, mercados de Cali", FEATURES, False, pipe(trees, FEATURES)),
        ("Regresión logística, todas, mercados de Cali", FEATURES, False, pipe(logistic, FEATURES)),
        ("HistGradientBoosting, todas, mercados de Cali", FEATURES, False, pipe(boosting, FEATURES)),
        ("HistGradientBoosting + ExtraTrees, todas, mercados de Cali", FEATURES, False,
         lambda: build_model(seed, FEATURES)),
    ]


def summarize(name, results):
    f1 = [r[0] for r in results]
    return {
        "variante": name,
        "f1_macro": round(float(np.mean(f1)), 4),
        "f1_peor_bloque": round(float(min(f1)), 4),
        "accuracy": round(float(np.mean([r[1] for r in results])), 4),
        "ahorro_simulado": round(float(np.mean([r[2] for r in results])), 4),
    }


def scores(test, pred):
    return (f1_score(test["clase"], pred, average="macro"), accuracy_score(test["clase"], pred),
            simulated_saving(test, pred))


def compare(panel, cfg, logger):
    market, seed = cfg["market"], cfg["model"]["random_state"]
    cavasa = panel[panel["mercado"] == market]
    tests = [evaluable(cavasa)[lambda d: d["semana_inicio"].isin(w)] for w in blocks(cavasa, cfg["model"]["test_weeks"])]

    rows = [
        summarize("Baseline: repetir la semana pasada", [
            scores(t, t["cambio_1s"].apply(classify, threshold=cfg["model"]["threshold"])) for t in tests]),
        summarize("Baseline: comprar todo hoy", [scores(t, ["sube"] * len(t)) for t in tests]),
    ]
    for name, features, only_cavasa, make in candidates(seed):
        source = evaluable(cavasa) if only_cavasa else panel.dropna(subset=["clase"])
        X, results = ["producto"] + list(features), []
        for test in tests:
            train = source[source["semana_inicio"] < test["semana_inicio"].min()]
            results.append(scores(test, make().fit(train[X], train["clase"]).predict(test[X])))
        rows.append(summarize(name, results))
        logger.info("%s", rows[-1])
    return pd.DataFrame(rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("experimentos")
    cfg = yaml.safe_load(Path("config/config.yaml").read_text(encoding="utf-8"))
    panel = pd.read_parquet(Path(cfg["paths"]["gold"]) / "entrenamiento.parquet")
    table = compare(panel, cfg, log)
    table.to_csv("docs/experimentos.csv", index=False)
    tracking.log_comparison(table, log)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
