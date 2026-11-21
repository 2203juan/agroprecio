import pandas as pd


from src.quality import check_gold, check_silver
from src.transform.gold_transformations import build_gold
from tests.conftest import PRODUCTS


def failed(result):
    return set(result.loc[~result["ok"], "regla"])


def test_clean_data_passes_all_rules(silver):
    assert failed(check_silver(silver)) == set()
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    assert failed(check_gold(gold, PRODUCTS)) == set()


def test_detects_negative_prices(silver):
    silver.loc[0, "precio_medio"] = -5
    assert "precios_positivos" in failed(check_silver(silver))


def test_detects_duplicates(silver):
    broken = pd.concat([silver, silver.iloc[[0]]], ignore_index=True)
    assert "sin_duplicados" in failed(check_silver(broken))


def test_detects_min_greater_than_max(silver):
    silver.loc[0, "precio_min"] = 99999
    assert "min_menor_o_igual_max" in failed(check_silver(silver))


def test_detects_missing_product(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    assert "todos_los_productos_presentes" in failed(check_gold(gold, PRODUCTS + ["Mora de Castilla"]))
