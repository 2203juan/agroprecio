import pandas as pd

from src.lista import cost_list, normalize_items
from src.model.monitor import product_accuracy
from src.model.predict import expected_range
from src.transform.gold_transformations import build_gold
from tests.conftest import PRODUCTS

ALERTS = pd.DataFrame({
    "producto": ["Tomate chonto", "Cilantro", "Papa capira"],
    "precio": [1000.0, 2000.0, 1500.0],
    "prediccion": ["sube", "baja", "estable"],
    "precio_min_esperado": [1100.0, 1700.0, 1450.0],
    "precio_max_esperado": [1300.0, 1900.0, 1550.0],
})


def test_cost_list_follows_recommendation():
    items = pd.DataFrame({"producto": ["Tomate chonto", "Cilantro", "Papa capira"], "kg_semana": [10, 2, 4]})
    rows, totals = cost_list(items, ALERTS)
    assert totals["costo_hoy"] == 10 * 1000 + 2 * 2000 + 4 * 1500
    # Tomate sube: se compra hoy. Cilantro baja: se espera (1800 en promedio). Papa estable: hoy.
    assert totals["costo_recomendado"] == 10 * 1000 + 2 * 1800 + 4 * 1500
    assert totals["costo_recomendado"] < totals["costo_proxima"]


def test_cost_list_empty():
    rows, totals = cost_list(pd.DataFrame(columns=["producto", "kg_semana"]), ALERTS)
    assert totals["costo_hoy"] == 0


def test_normalize_items_drops_unknown_and_zero():
    items = [{"producto": "Tomate chonto", "kg_semana": 5}, {"producto": "Uva", "kg_semana": 3},
             {"producto": "Cilantro", "kg_semana": 0}, {"producto": "Tomate chonto", "kg_semana": 8}]
    df = normalize_items(items, PRODUCTS)
    assert df.to_dict("records") == [{"producto": "Tomate chonto", "kg_semana": 8}]


def test_expected_range_matches_predicted_direction(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    latest = gold.dropna(subset=["cambio_1s"]).groupby("producto").tail(1)
    alerts = latest[["producto", "precio"]].assign(prediccion="sube")
    out = expected_range(gold, alerts)
    assert (out["precio_min_esperado"] <= out["precio_max_esperado"]).all()
    assert (out["precio_min_esperado"] > out["precio"]).all()


def test_product_accuracy_counts_last_weeks():
    weeks = pd.date_range("2026-01-03", periods=10, freq="7D")
    scored = pd.DataFrame({"semana_inicio": weeks, "producto": "Cilantro", "acierto": [False] * 2 + [True] * 8})
    acc = product_accuracy(scored, weeks=8)
    assert acc.iloc[0]["aciertos"] == 8 and acc.iloc[0]["evaluadas"] == 8
