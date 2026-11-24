import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PRODUCTS = ["Tomate chonto", "Cilantro"]  # el diario trae tomate, pero no cilantro


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


def weekly_title(start):
    end = start + pd.Timedelta(days=6)
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
              "septiembre", "octubre", "noviembre", "diciembre"]
    return (f"Boletín semanal precios mayoristas - {start.day} de {months[start.month - 1]} "
            f"al {end.day} de {months[end.month - 1]} de {end.year}")


@pytest.fixture
def cfg(tmp_path):
    """Configuración completa apuntando a una carpeta temporal."""
    for layer in ["bronze", "silver", "gold"]:
        (tmp_path / layer).mkdir()
    return {
        "paths": {"bronze": str(tmp_path / "bronze"), "silver": str(tmp_path / "silver"),
                  "gold": str(tmp_path / "gold"), "models": str(tmp_path / "models"),
                  "logs": str(tmp_path / "logs"), "database": str(tmp_path / "gold" / "test.db")},
        "market": "Cali, Cavasa", "products": PRODUCTS,
        "model": {"threshold": 0.03, "test_weeks": 6, "min_history_weeks": 8, "random_state": 42},
        "monitoring": {"drift_zscore": 3.0, "min_accuracy": 0.40},
        "llm": {"model": "modelo-de-prueba", "max_tokens": 100},
    }


@pytest.fixture
def bronze(cfg):
    """Cuarenta boletines con un patrón de precios que se puede aprender."""
    for w, week in enumerate(pd.date_range("2026-01-03", periods=40, freq="7D")):
        rows = []
        for p, product in enumerate(PRODUCTS):
            for market, factor in [("Cali, Cavasa", 1.0), ("Bogotá, D.C., Corabastos", 0.9)]:
                price = round((3000 + [0, 400, 400, 800][(w + p) % 4]) * factor)  # sube, estable, sube, baja
                rows.append((product, market, price - 100, price + 100, price, "="))
        write_bulletin(Path(cfg["paths"]["bronze"]) / f"sipsa_{w:04d}.xlsx", weekly_title(week), rows)
    folder = Path(cfg["paths"]["bronze"]) / "diario"
    folder.mkdir()
    raw_daily(pd.date_range("2026-01-03", periods=40, freq="7D")).to_parquet(folder / "sipsa_diario.parquet")
    return cfg


def raw_daily(weeks, products=("Tomate", "Aguacate")):
    """Diario como lo entrega el servicio del DANE (todo texto): Cavasa lunes y jueves,
    Corabastos de lunes a viernes. El jueves cierra 4 % por encima del lunes."""
    rows = []
    for w, week in enumerate(weeks):
        for p, product in enumerate(products):
            base = 3000 + [0, 400, 400, 800][(w + p) % 4]
            for market, days in [("Cali, Cavasa", (2, 5)), ("Bogotá, D.C., Corabastos", (2, 3, 4, 5, 6))]:
                for k, offset in enumerate(days):
                    price = round(base * (0.98 + 0.04 * k / (len(days) - 1)))
                    rows.append({
                        "enmaFecha": f"{(week + pd.Timedelta(days=offset)).date()}T00:00:00-05:00",
                        "artiNombre": product + "*", "fuenNombre": market, "grupNombre": "FRUTAS",
                        "promedioKg": str(price), "minimoKg": str(price - 100), "maximoKg": str(price + 100),
                    })
    return pd.DataFrame(rows)


@pytest.fixture(autouse=True)
def sin_servicios_externos(monkeypatch):
    """Ningún test llama al modelo de lenguaje ni a MLflow."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
