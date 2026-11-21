import pandas as pd

from src.extract.extract_excel import parse_week, read_bulletin


def test_parse_week_same_month():
    start, end = parse_week("Boletín semanal precios mayoristas - 12 al 16 de abril de 2025")
    assert start == pd.Timestamp(2025, 4, 12)
    assert end == pd.Timestamp(2025, 4, 16)


def test_parse_week_two_months():
    start, end = parse_week("Boletín semanal precios mayoristas - 31 de octubre al 6 de noviembre de 2026")
    assert start == pd.Timestamp(2026, 10, 31)
    assert end == pd.Timestamp(2026, 11, 6)


def test_parse_week_two_years():
    start, end = parse_week("Boletín semanal precios mayoristas - 30 de diciembre de 2023 a 5 de enero de 2024")
    assert start == pd.Timestamp(2023, 12, 30)
    assert end == pd.Timestamp(2024, 1, 5)


def test_parse_week_december_to_january_without_year():
    start, _ = parse_week("Boletín semanal - 28 de diciembre al 3 de enero de 2025")
    assert start == pd.Timestamp(2024, 12, 28)


def test_read_bulletin(bulletin_file):
    df = read_bulletin(bulletin_file)
    assert len(df) == 3
    assert set(df.columns) >= {"producto", "mercado", "precio_medio", "semana_inicio", "grupo"}
    assert df["grupo"].iloc[0] == "Verduras y hortalizas"
    assert df["semana_inicio"].iloc[0] == pd.Timestamp(2026, 10, 31)
    cavasa = df[(df["producto"] == "Tomate chonto") & (df["mercado"] == "Cali, Cavasa")]
    assert cavasa["precio_medio"].iloc[0] == 3200
