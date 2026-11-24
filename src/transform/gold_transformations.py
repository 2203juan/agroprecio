"""Capa gold: serie semanal de Cavasa por producto, con las variables del modelo.

También arma la tabla de entrenamiento: las mismas variables para todos los mercados de
Cali, que le dan al modelo más ejemplos de cómo se mueven los precios en la ciudad.
"""
import numpy as np
import pandas as pd

from src.transform.diario import DAILY_FEATURES, add_daily_features

# Variables de las versiones v0.1 a v0.5. Una fila es evaluable si las tiene todas
BASE_FEATURES = ["cambio_1s", "cambio_2s", "cambio_4s", "vs_media_4s",
                 "vs_nacional", "cambio_nacional_1s", "mes"]

# Historia del producto en su propio mercado
OWN = ["cambio_1s", "cambio_2s", "cambio_3s", "cambio_4s", "cambio_8s", "cambio_1s_hace_1",
       "cambio_1s_hace_2", "vs_media_4s", "vs_media_8s", "vs_media_13s", "vs_media_26s",
       "volatilidad_8s", "posicion_26s", "rango_relativo", "asimetria", "tendencia_dane",
       "cambio_anio_anterior"]
# Qué pasa con ese producto en el país, en la región y en Corabastos
MARKET = ["mediana_cambio_nacional", "mediana_cambio_nacional_hace_1", "cambio_nacional_4s",
          "cambio_nacional_1s", "amplitud_nacional", "vs_nacional", "vs_nacional_desviacion",
          "cambio_relativo", "cambio_corabastos", "vs_corabastos", "cambio_regional",
          "vs_regional", "cambio_grupo"]
SEASON = ["estacion_sen", "estacion_cos", "mes"]
# Las de v0.6, que salen solo del boletín semanal
WEEKLY_FEATURES = OWN + MARKET + SEASON
# Desde v0.7 se suma cómo cerró la semana según el diario del SIPSA
FEATURES = WEEKLY_FEATURES + DAILY_FEATURES

REFERENCE_MARKET = "Bogotá, D.C., Corabastos"
REGION = "Valle del Cauca|Armenia|Pereira|Popayán"
TREND = {"+": 1, "++": 2, "+++": 3, "-": -1, "--": -2, "---": -3, "=": 0}


def classify(change, threshold):
    if pd.isna(change):
        return None
    if change > threshold:
        return "sube"
    if change < -threshold:
        return "baja"
    return "estable"


def own_history(df):
    """Variables de cada serie (mercado y producto). Solo miran hacia atrás."""
    g = df.groupby(["mercado", "producto"], sort=False)
    price = g["precio"]
    for k in (1, 2, 3, 4, 8):
        df[f"cambio_{k}s"] = price.pct_change(k)
    df["cambio_1s_hace_1"] = g["cambio_1s"].shift(1)
    df["cambio_1s_hace_2"] = g["cambio_1s"].shift(2)
    df["vs_media_4s"] = df["precio"] / price.transform(lambda s: s.rolling(4).mean()) - 1
    for k in (8, 13, 26):
        df[f"vs_media_{k}s"] = df["precio"] / price.transform(lambda s: s.rolling(k, min_periods=k // 2).mean()) - 1
    df["volatilidad_8s"] = g["cambio_1s"].transform(lambda s: s.rolling(8, min_periods=4).std())
    low = price.transform(lambda s: s.rolling(26, min_periods=8).min())
    high = price.transform(lambda s: s.rolling(26, min_periods=8).max())
    df["posicion_26s"] = (df["precio"] - low) / (high - low + 1)
    df["rango_relativo"] = (df["precio_max"] - df["precio_min"]) / df["precio"]
    df["asimetria"] = (df["precio_max"] + df["precio_min"] - 2 * df["precio"]) / df["precio"]
    df["tendencia_dane"] = df["tendencia"].map(TREND)
    return df


def add_target(df, threshold):
    """Objetivo: qué pasa con el precio la semana siguiente."""
    g = df.groupby(["mercado", "producto"], sort=False)
    df["precio_siguiente"] = g["precio"].shift(-1)
    consecutive = (g["semana_inicio"].shift(-1) - df["semana_inicio"]).dt.days == 7
    df.loc[~consecutive, "precio_siguiente"] = np.nan
    df["cambio_siguiente"] = df["precio_siguiente"] / df["precio"] - 1
    df["clase"] = df["cambio_siguiente"].apply(classify, threshold=threshold)
    # Lo que pasó con ese producto la misma semana del año pasado
    last_year = df[["mercado", "producto", "semana_inicio", "cambio_siguiente"]].copy()
    last_year["semana_inicio"] += pd.Timedelta(days=364)
    last_year = last_year.rename(columns={"cambio_siguiente": "cambio_anio_anterior"})
    return df.merge(last_year, on=["mercado", "producto", "semana_inicio"], how="left")


def add_market_context(df, market):
    key = ["producto", "semana_inicio"]
    national = df.groupby(key).agg(
        precio_nacional=("precio", "median"),
        mediana_cambio_nacional=("cambio_1s", "median"),
        amplitud_nacional=("cambio_1s", lambda c: (c > 0.03).mean() - (c < -0.03).mean()),
    ).reset_index().sort_values(key)
    by_product = national.groupby("producto")
    national["mediana_cambio_nacional_hace_1"] = by_product["mediana_cambio_nacional"].shift(1)
    national["cambio_nacional_mediana_1s"] = by_product["precio_nacional"].pct_change(1)
    national["cambio_nacional_4s"] = by_product["precio_nacional"].pct_change(4)
    df = df.merge(national, on=key, how="left")
    df["vs_nacional"] = df["precio"] / df["precio_nacional"] - 1
    usual_gap = (df.sort_values("semana_inicio").groupby(["mercado", "producto"])["vs_nacional"]
                 .transform(lambda s: s.rolling(26, min_periods=8).mean()))
    df["vs_nacional_desviacion"] = df["vs_nacional"] - usual_gap
    df["cambio_relativo"] = df["cambio_1s"] - df["mediana_cambio_nacional"]

    reference = df.loc[df["mercado"] == REFERENCE_MARKET, key + ["cambio_1s", "precio"]]
    df = df.merge(reference.rename(columns={"cambio_1s": "cambio_corabastos", "precio": "_corabastos"}),
                  on=key, how="left")
    df["vs_corabastos"] = df["precio"] / df["_corabastos"] - 1

    regional = (df["mercado"].str.startswith("Cali") | df["mercado"].str.contains(REGION)) & (df["mercado"] != market)
    region = df[regional].groupby(key).agg(cambio_regional=("cambio_1s", "median"), _regional=("precio", "median"))
    df = df.merge(region.reset_index(), on=key, how="left")
    df["vs_regional"] = df["precio"] / df["_regional"] - 1

    group = df.groupby(["mercado", "grupo", "semana_inicio"])["cambio_1s"].mean().rename("cambio_grupo")
    df = df.merge(group.reset_index(), on=["mercado", "grupo", "semana_inicio"], how="left")
    return df.drop(columns=["_corabastos", "_regional"])


def build_panel(silver, market, products, threshold, daily=None):
    """Variables y objetivo para los mercados de Cali (incluye `market`).
    daily: precios diarios en silver. Sin ellos, las variables del diario quedan vacías."""
    # En silver los textos son categorías; aquí quedan como texto normal
    df = silver.loc[silver["producto"].isin(products),
                    ["semana_inicio", "grupo", "producto", "mercado", "precio_min", "precio_max",
                     "precio_medio", "tendencia"]]
    df = df.astype({"producto": str, "grupo": str, "mercado": str, "tendencia": str})
    df = df.rename(columns={"precio_medio": "precio"})
    df = df.sort_values(["mercado", "producto", "semana_inicio"]).reset_index(drop=True)

    df = add_market_context(add_target(own_history(df), threshold), market)

    # Cambio de la mediana nacional en las semanas en que hay dato de ese mercado
    df = df.sort_values(["mercado", "producto", "semana_inicio"])
    df["cambio_nacional_1s"] = df.groupby(["mercado", "producto"])["precio_nacional"].pct_change(1)
    angle = df["semana_inicio"].dt.day_of_year * 2 * np.pi / 365.25
    df["estacion_sen"], df["estacion_cos"] = np.sin(angle), np.cos(angle)
    df["mes"] = df["semana_inicio"].dt.month
    city = market.split(",")[0]
    keep = ["mercado", "producto", "grupo", "semana_inicio", "precio", "precio_nacional", *WEEKLY_FEATURES,
            "precio_siguiente", "cambio_siguiente", "clase"]
    panel = add_daily_features(df.loc[df["mercado"].str.startswith(city), keep], daily)
    target = ["precio_siguiente", "cambio_siguiente", "clase"]
    return panel[[c for c in panel if c not in target] + target].reset_index(drop=True)


def gold_from_panel(panel, market):
    gold = panel[panel["mercado"] == market].drop(columns="mercado")
    return gold.sort_values(["producto", "semana_inicio"]).reset_index(drop=True)


def build_gold(silver, market, products, threshold, daily=None):
    return gold_from_panel(build_panel(silver, market, products, threshold, daily), market)
