"""Limpieza de bronze a silver: una fila por semana, producto y mercado."""
import pandas as pd

PRICE_COLS = ["precio_min", "precio_max", "precio_medio"]


def normalize_text(s):
    return s.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def clean_prices(raw):
    df = raw.copy()

    for col in ["producto", "mercado", "grupo"]:
        df[col] = normalize_text(df[col])

    # El DANE cambió el nombre de este grupo entre años
    df["grupo"] = df["grupo"].replace({"Lácteos y huevos": "Huevos y lácteos"})

    for col in PRICE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["tendencia"] = df["tendencia"].astype(str).str.strip().replace({"nan": None})

    # Filas sin fecha o sin precio no sirven
    df = df.dropna(subset=["semana_inicio", "precio_medio"])
    df = df[df["precio_medio"] > 0]

    # Si el mínimo o el máximo vienen vacíos, usamos el precio medio
    df["precio_min"] = df["precio_min"].fillna(df["precio_medio"])
    df["precio_max"] = df["precio_max"].fillna(df["precio_medio"])

    # Algunos boletines repiten la misma fila; nos quedamos con la primera
    df = df.drop_duplicates(subset=["semana_inicio", "producto", "mercado"], keep="first")

    df["semana_inicio"] = pd.to_datetime(df["semana_inicio"])
    df["semana_fin"] = pd.to_datetime(df["semana_fin"])
    df["anio"] = df["semana_inicio"].dt.year

    cols = ["semana_inicio", "semana_fin", "anio", "grupo", "producto", "mercado",
            "precio_min", "precio_max", "precio_medio", "tendencia", "archivo"]
    return df[cols].sort_values(["semana_inicio", "producto", "mercado"]).reset_index(drop=True)
