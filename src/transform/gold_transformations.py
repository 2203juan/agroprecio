"""Capa gold: serie semanal de Cavasa por producto, con las variables del modelo."""
import pandas as pd

FEATURES = ["cambio_1s", "cambio_2s", "cambio_4s", "vs_media_4s",
            "vs_nacional", "cambio_nacional_1s", "mes"]


def classify(change, threshold):
    if pd.isna(change):
        return None
    if change > threshold:
        return "sube"
    if change < -threshold:
        return "baja"
    return "estable"


def build_gold(silver, market, products, threshold):
    # Precio nacional de referencia: mediana de todos los mercados
    national = (silver[silver["producto"].isin(products)]
                .groupby(["producto", "semana_inicio"], as_index=False)["precio_medio"].median()
                .rename(columns={"precio_medio": "precio_nacional"}))

    local = (silver[(silver["mercado"] == market) & (silver["producto"].isin(products))]
             [["producto", "grupo", "semana_inicio", "precio_medio"]]
             .rename(columns={"precio_medio": "precio"}))

    df = local.merge(national, on=["producto", "semana_inicio"], how="left")
    df = df.sort_values(["producto", "semana_inicio"]).reset_index(drop=True)

    g = df.groupby("producto")
    df["cambio_1s"] = g["precio"].pct_change(1)
    df["cambio_2s"] = g["precio"].pct_change(2)
    df["cambio_4s"] = g["precio"].pct_change(4)
    df["vs_media_4s"] = df["precio"] / g["precio"].transform(lambda s: s.rolling(4).mean()) - 1
    df["vs_nacional"] = df["precio"] / df["precio_nacional"] - 1
    df["cambio_nacional_1s"] = g["precio_nacional"].pct_change(1)
    df["mes"] = df["semana_inicio"].dt.month

    # Objetivo: qué pasa con el precio la semana siguiente
    df["precio_siguiente"] = g["precio"].shift(-1)
    next_date = g["semana_inicio"].shift(-1)
    consecutive = (next_date - df["semana_inicio"]).dt.days == 7
    df.loc[~consecutive, "precio_siguiente"] = None
    df["cambio_siguiente"] = df["precio_siguiente"] / df["precio"] - 1
    df["clase"] = df["cambio_siguiente"].apply(classify, threshold=threshold)

    return df
