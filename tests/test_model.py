import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

import main
from src.model.experiments import blocks
from src.model.metrics import evaluate_version
from src.model.predict import predict_latest
from src.model.train import evaluated_model, load_production, training_rows, usable_features
from src.transform.gold_transformations import BASE_FEATURES, FEATURES, build_gold, build_panel
from tests.conftest import PRODUCTS

MARKET = "Cali, Cavasa"


@pytest.fixture
def wide_silver(silver):
    """El silver de prueba con un segundo mercado de Cali."""
    extra = silver[silver["mercado"] == MARKET].assign(mercado="Cali, Santa Elena")
    extra[["precio_min", "precio_max", "precio_medio"]] += 150
    return pd.concat([silver, extra], ignore_index=True)


def test_panel_keeps_only_the_city(wide_silver):
    panel = build_panel(wide_silver, MARKET, PRODUCTS, 0.03)
    assert set(panel["mercado"]) == {MARKET, "Cali, Santa Elena"}
    gold = build_gold(wide_silver, MARKET, PRODUCTS, 0.03)
    assert len(gold) == (panel["mercado"] == MARKET).sum() and "mercado" not in gold


def test_features_do_not_look_into_the_future(wide_silver):
    """Quitar las últimas semanas no cambia las variables de las anteriores."""
    cut = wide_silver["semana_inicio"].max() - pd.Timedelta(weeks=5)
    key = ["mercado", "producto", "semana_inicio"]
    full = build_panel(wide_silver, MARKET, PRODUCTS, 0.03)
    full = full[full["semana_inicio"] <= cut].set_index(key)[FEATURES].sort_index()
    past = build_panel(wide_silver[wide_silver["semana_inicio"] <= cut], MARKET, PRODUCTS, 0.03)
    past = past.set_index(key)[FEATURES].sort_index()
    pd.testing.assert_frame_equal(full, past)


def test_training_rows_stop_before_the_test(wide_silver):
    panel = build_panel(wide_silver, MARKET, PRODUCTS, 0.03)
    cut = panel["semana_inicio"].max() - pd.Timedelta(weeks=4)
    rows = training_rows(panel, before=cut)
    assert rows["semana_inicio"].max() < cut and rows["clase"].notna().all()


def test_empty_features_are_left_out(wide_silver):
    panel = build_panel(wide_silver, MARKET, PRODUCTS, 0.03)  # 20 semanas: no hay año anterior
    assert "cambio_anio_anterior" not in usable_features(panel)


def test_metrics_come_from_the_model_that_did_not_see_the_test(bronze):
    main.run(bronze, download=False)
    models = Path(bronze["paths"]["models"])
    entry = load_production(models)[1]
    gold = pd.read_parquet(main.gold_path(bronze))
    rows, _, _ = evaluate_version(evaluated_model(models, entry["version"]), entry, gold, bronze)
    assert rows[0]["f1_macro"] == entry["metricas"]["modelo"]["f1_macro"]
    assert (models / f"{entry['version']}_prueba.joblib").exists()
    assert entry["datos"]["filas_produccion"] > entry["datos"]["filas_entrenamiento"]


def test_versions_before_v06_still_work(bronze):
    """Una versión anterior solo tenía un archivo y las variables básicas."""
    from sklearn.dummy import DummyClassifier

    for stage in ["silver", "gold"]:
        main.STAGES[stage](bronze, logging.getLogger("test"))
    gold = pd.read_parquet(main.gold_path(bronze))
    known = gold.dropna(subset=BASE_FEATURES + ["clase"])
    models = Path(bronze["paths"]["models"])
    models.mkdir()
    joblib.dump(DummyClassifier(strategy="prior").fit(known[["producto"] + BASE_FEATURES], known["clase"]),
                models / "v1.joblib")
    entry = {"version": "v1", "estado": "produccion", "features": BASE_FEATURES, "metricas": {},
             "datos": {"hasta": str(known["semana_inicio"].max().date())}}
    (models / "registry.json").write_text(json.dumps([entry]))

    model, loaded = load_production(models)
    assert len(predict_latest(gold, model, loaded)) == len(PRODUCTS)
    assert evaluate_version(evaluated_model(models, "v1"), loaded, gold, bronze)[0]


def test_experiments_never_touch_the_test_weeks():
    weeks = pd.date_range("2023-01-07", periods=130, freq="7D")
    gold = pd.DataFrame({"semana_inicio": weeks, "clase": "sube", **{f: 0.0 for f in BASE_FEATURES}})
    used = np.concatenate(blocks(gold, test_weeks=20))
    assert used.max() < weeks[-20] and len(set(used)) == 5 * 14


def test_low_confidence_is_not_recommended():
    from src.model.predict import recommend

    prediction = pd.Series(["sube", "baja", "estable", "sube"])
    rec, signal = recommend(prediction, [0.62, 0.41, 0.45, 0.50], 0.50)
    assert rec.tolist() == ["sube", "estable", "estable", "sube"]
    assert signal.tolist() == ["clara", "debil", "debil", "clara"]


def test_clear_signal_reports_coverage_and_accuracy():
    from src.model.metrics import clear_signal

    proba = np.array([[0.7, 0.2, 0.1], [0.4, 0.3, 0.3], [0.1, 0.1, 0.8], [0.2, 0.6, 0.2]])
    out = clear_signal(["baja", "sube", "baja", "estable"], ["baja", "baja", "sube", "estable"], proba, 0.5)
    assert out == {"cobertura_senal_clara": 0.75, "accuracy_senal_clara": 0.6667}


def test_alerts_carry_the_signal(bronze):
    bronze["model"]["min_confidence"] = 0.5
    main.run(bronze, download=False)
    from src.load.load_database import read_table

    alerts = read_table("alertas", bronze["paths"]["database"])
    weak = alerts[alerts["confianza"] < 0.5]
    assert set(alerts["senal"]) <= {"clara", "debil"}
    assert (weak["recomendacion"] == "estable").all() and (weak["accion"] == "Compra normal").all()
    assert "recomendacion" in read_table("predicciones", bronze["paths"]["database"])
