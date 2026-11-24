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


def test_real_savings_uses_real_next_price():
    from src.lista import real_savings

    items = pd.DataFrame({"producto": ["Tomate chonto", "Cilantro"], "kg_semana": [10, 2]})
    history = pd.DataFrame({
        "semana_inicio": ["2026-01-03"] * 2 + ["2026-01-10"] * 2,
        "producto": ["Tomate chonto", "Cilantro"] * 2,
        "prediccion": ["baja", "sube", "baja", "estable"],
        "precio": [1000.0, 2000.0, 900.0, 2100.0],
        "precio_siguiente": [900.0, 2100.0, 1000.0, None],  # la última no tiene resultado todavía
    })
    out = real_savings(items, history)
    first, second = out["semanas"]
    # Semana 1: acertó que el tomate bajaba y se ahorró 10 kg x $100
    assert first["ahorro"] == 1000
    # Semana 2: dijo que bajaba y subió: esperar costó $1.000 más
    assert second["ahorro"] == -1000
    r = out["resumen"]
    assert r["semanas"] == 2 and r["ahorro"] == 0
    assert r["semanas_con_ahorro"] == 1 and r["semanas_con_perdida"] == 1
    assert r["ahorro_maximo_posible"] == 1000
    # Dos veces dijo "espera" y acertó una; en esas compras el ahorro neto fue cero
    assert r["esperas"] == 2 and r["esperas_acertadas"] == 1 and r["ahorro_en_esperas_pct"] == 0
    assert r["mejor_semana"] == {"semana_inicio": "2026-01-03", "ahorro": 1000.0, "ahorro_pct": 0.0714}


def test_real_savings_empty_list():
    from src.lista import real_savings

    out = real_savings(pd.DataFrame(columns=["producto", "kg_semana"]), pd.DataFrame())
    assert out == {"semanas": [], "resumen": None}


def test_costs_follow_the_recommendation_not_the_raw_prediction():
    alerts = ALERTS.assign(recomendacion=["sube", "estable", "estable"])  # el cilantro quedó sin señal clara
    items = pd.DataFrame({"producto": ["Cilantro"], "kg_semana": [2]})
    _, totals = cost_list(items, alerts)
    assert totals["costo_recomendado"] == totals["costo_hoy"]
