import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PRODUCTS = ["Tomate chonto", "Cilantro"]


def write_bulletin(path, title, rows):
    """Crea un Excel con la misma forma que el boletín semanal del SIPSA."""
    wb = Workbook()
    index = wb.active
    index.title = "Índice"
    index["A3"] = "SISTEMA DE INFORMACIÓN DE PRECIOS -SIPSA-"
    index["A5"] = title

    sheet = wb.create_sheet("1.1")
    sheet["A6"] = "1.1. Verduras y hortalizas"
    sheet["A10"], sheet["B10"], sheet["C10"], sheet["F10"] = "Producto", "Mercado mayorista", "Pesos por kilogramo", "Tendencia*"
    sheet["C11"], sheet["D11"], sheet["E11"] = "Precio mínimo", "Precio máximo", "Precio medio"
    for i, row in enumerate(rows, start=12):
        for j, value in enumerate(row, start=1):
            sheet.cell(row=i, column=j, value=value)
    wb.save(path)


@pytest.fixture
def bulletin_file(tmp_path):
    path = tmp_path / "sipsa_0001.xlsx"
    write_bulletin(path, "Boletín semanal precios mayoristas - 31 de octubre al 6 de noviembre de 2026", [
        ("Tomate chonto", "Cali, Cavasa", 3000, 3400, 3200, "+"),
        ("Tomate chonto", "Bogotá, D.C., Corabastos", 2800, 3000, 2900, "="),
        ("Cilantro", "Cali, Cavasa", 4000, 4500, 4200, "-"),
    ])
    return path


@pytest.fixture
def silver():
    """Veinte semanas de precios sintéticos para dos productos y dos mercados."""
    weeks = pd.date_range("2026-01-03", periods=20, freq="7D")
    rows = []
    for w, week in enumerate(weeks):
        for p, product in enumerate(PRODUCTS):
            for market, factor in [("Cali, Cavasa", 1.0), ("Bogotá, D.C., Corabastos", 0.9)]:
                price = 3000 + 400 * ((w + p) % 4) * factor
                rows.append({
                    "semana_inicio": week, "semana_fin": week + pd.Timedelta(days=6),
                    "anio": week.year, "grupo": "Verduras y hortalizas", "producto": product,
                    "mercado": market, "precio_min": price - 100, "precio_max": price + 100,
                    "precio_medio": price, "tendencia": "=", "archivo": "x.xlsx",
                })
    return pd.DataFrame(rows)
