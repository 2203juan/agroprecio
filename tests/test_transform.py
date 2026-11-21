import pandas as pd

from src.extract.extract_excel import read_bulletin
from src.transform.clean_excel import clean_prices
from src.transform.gold_transformations import build_gold, classify
from tests.conftest import PRODUCTS


def test_clean_removes_bad_rows_and_duplicates(bulletin_file):
    raw = read_bulletin(bulletin_file)
    bad = raw.iloc[[0]].assign(precio_medio="n.d.")
    dup = raw.iloc[[1]]
    clean = clean_prices(pd.concat([raw, bad, dup], ignore_index=True))
    assert len(clean) == 3
    assert clean["precio_medio"].dtype.kind in "if"


def test_clean_normalizes_spaces(bulletin_file):
    raw = read_bulletin(bulletin_file)
    raw.loc[0, "producto"] = "  Tomate   chonto "
    clean = clean_prices(raw)
    assert "Tomate chonto" in clean["producto"].values


def test_classify():
    assert classify(0.05, 0.03) == "sube"
    assert classify(-0.05, 0.03) == "baja"
    assert classify(0.01, 0.03) == "estable"
    assert classify(float("nan"), 0.03) is None


def test_gold_has_one_row_per_product_and_week(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    assert len(gold) == 20 * len(PRODUCTS)
    assert not gold.duplicated(["producto", "semana_inicio"]).any()


def test_gold_target_is_next_week(silver):
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)
    tomato = gold[gold["producto"] == "Tomate chonto"].reset_index(drop=True)
    assert tomato.loc[0, "precio_siguiente"] == tomato.loc[1, "precio"]
    assert pd.isna(tomato["clase"].iloc[-1])  # la última semana todavía no tiene resultado


def test_gold_breaks_target_when_a_week_is_missing(silver):
    missing = silver["semana_inicio"].drop_duplicates().iloc[5]
    gold = build_gold(silver[silver["semana_inicio"] != missing], "Cali, Cavasa", PRODUCTS, 0.03)
    before_gap = gold[gold["semana_inicio"] == missing - pd.Timedelta(days=7)]
    assert before_gap["clase"].isna().all()


def test_clean_unifies_group_names(bulletin_file):
    raw = read_bulletin(bulletin_file)
    raw.loc[0, "grupo"] = "Lácteos y huevos"
    raw.loc[1, "grupo"] = "Huevos y lácteos"
    clean = clean_prices(raw)
    assert "Lácteos y huevos" not in clean["grupo"].values
