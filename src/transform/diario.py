"""Limpieza del diario del SIPSA y variables que salen de él.

El boletín semanal da el promedio de la semana (sábado a viernes). El diario dice además
cómo se movió el precio por dentro: si Cavasa cerró el jueves por encima de su promedio,
o si Corabastos subió de lunes a viernes, lo normal es que la semana siguiente arranque
desde ahí. Todas las variables usan solo días de la misma semana o anteriores.
"""
import pandas as pd

# Nombre del producto en el diario (en minúsculas). El diario no trae cilantro, y trae una
# sola "papa negra" para las dos papas del proyecto
PRODUCT = {
    "Aguacate papelillo": "aguacate", "Ahuyama": "ahuyama",
    "Cebolla cabezona blanca bogotana": "cebolla cabezona blanca", "Cebolla junca Aquitania": "cebolla junca",
    "Habichuela": "habichuela", "Lechuga Batavia": "lechuga batavia", "Limón Tahití": "limón tahití",
    "Lulo": "lulo", "Mango Tommy": "mango tommy", "Maracuyá": "maracuyá", "Mora de Castilla": "mora de castilla",
    "Papa capira": "papa negra", "Papa parda pastusa": "papa negra", "Pimentón": "pimentón",
    "Plátano hartón verde": "plátano hartón verde", "Tomate chonto": "tomate", "Tomate de árbol": "tomate de árbol",
    "Yuca ICA": "yuca", "Zanahoria bogotana": "zanahoria",
}
# En estos tres el diario no es el mismo producto del boletín semanal (otra variedad o no
# se reporta en Cavasa): sirven como contexto del país, pero no como precio propio
APPROXIMATE = {"Papa parda pastusa", "Zanahoria bogotana", "Yuca ICA"}
MARKET_FIXES = {"Cali, Santa Helena": "Cali, Santa Elena"}
REFERENCE = "Bogotá, D.C., Corabastos"
REGION = ["Armenia, Mercar", "Pereira, Mercasa", "Pereira, La 41", "Pereira, La 41-Impala",
          "Popayán, Plaza de mercado del barrio Bolívar", "Cali, Santa Elena", "Cali, Cavasa"]

OWN_DAILY = ["dia_ultimo_vs_semana", "dia_cambio_intra", "dia_cambio_cierre"]
CONTEXT_DAILY = ["cora_cierre_vs_media", "cora_cambio_intra", "cora_cambio_cierre",
                 "region_cierre_vs_media", "pais_cierre_vs_media", "pais_amplitud_intra"]
DAILY_FEATURES = OWN_DAILY + CONTEXT_DAILY


def clean_daily(raw):
    """De bronze a silver: una fila por día, producto y mercado, con precios numéricos."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime(raw["enmaFecha"].str[:10]),
        # El asterisco marca "variedad predominante en el mercado"
        "producto": raw["artiNombre"].str.replace("*", " ", regex=False).str.split().str.join(" "),
        "mercado": raw["fuenNombre"].str.split().str.join(" ").replace(MARKET_FIXES),
        "precio": pd.to_numeric(raw["promedioKg"], errors="coerce"),
        "precio_min": pd.to_numeric(raw["minimoKg"], errors="coerce"),
        "precio_max": pd.to_numeric(raw["maximoKg"], errors="coerce"),
    })
    df = df.dropna(subset=["fecha", "producto", "mercado", "precio"])
    df = df[df["precio"] > 0].drop_duplicates(["fecha", "producto", "mercado"], keep="last")
    return df.sort_values(["fecha", "mercado", "producto"]).reset_index(drop=True)


def week_start(dates):
    """Sábado en que empieza la semana del boletín (sábado a viernes)."""
    return dates - pd.to_timedelta((dates.dt.day_of_week - 5) % 7, unit="D")


def weekly_summary(daily):
    """Por semana, producto y mercado: primer precio, último, promedio y cambio del cierre."""
    d = daily.copy()
    d["producto"] = d["producto"].str.lower()
    d["semana_inicio"] = week_start(d["fecha"])
    d = d.sort_values("fecha")
    w = d.groupby(["mercado", "producto", "semana_inicio"]).agg(
        primero=("precio", "first"), ultimo=("precio", "last"), media=("precio", "mean"), dias=("precio", "size"),
    ).reset_index()
    w["cierre_vs_media"] = w["ultimo"] / w["media"] - 1
    w["cambio_intra"] = (w["ultimo"] / w["primero"] - 1).where(w["dias"] > 1)
    # Cierre de esta semana contra el cierre de la semana anterior (si es la semana anterior)
    w = w.sort_values(["mercado", "producto", "semana_inicio"])
    g = w.groupby(["mercado", "producto"])
    consecutive = (w["semana_inicio"] - g["semana_inicio"].shift(1)).dt.days == 7
    w["cambio_cierre"] = (w["ultimo"] / g["ultimo"].shift(1) - 1).where(consecutive)
    return w


def add_daily_features(panel, daily):
    """Agrega DAILY_FEATURES a la tabla de entrenamiento (mercado, producto, semana_inicio)."""
    out = panel.copy()
    if daily is None or daily.empty:
        return out.assign(**{f: float("nan") for f in DAILY_FEATURES})
    w = weekly_summary(daily)
    out["_diario"] = out["producto"].map(PRODUCT)
    key = ["_diario", "semana_inicio"]

    own = w.rename(columns={"producto": "_diario", "ultimo": "_ultimo", "cambio_intra": "dia_cambio_intra",
                            "cambio_cierre": "dia_cambio_cierre"})
    out = out.merge(own[["mercado", *key, "_ultimo", "dia_cambio_intra", "dia_cambio_cierre"]],
                    on=["mercado", *key], how="left")
    out["dia_ultimo_vs_semana"] = out["_ultimo"] / out["precio"] - 1
    out.loc[out["producto"].isin(APPROXIMATE), OWN_DAILY] = float("nan")

    ref = w[w["mercado"] == REFERENCE].rename(columns={
        "producto": "_diario", "cierre_vs_media": "cora_cierre_vs_media",
        "cambio_intra": "cora_cambio_intra", "cambio_cierre": "cora_cambio_cierre"})
    out = out.merge(ref[[*key, "cora_cierre_vs_media", "cora_cambio_intra", "cora_cambio_cierre"]], on=key, how="left")

    region = (w[w["mercado"].isin(REGION)].groupby(["producto", "semana_inicio"])["cierre_vs_media"]
              .median().rename("region_cierre_vs_media").reset_index().rename(columns={"producto": "_diario"}))
    country = w.groupby(["producto", "semana_inicio"]).agg(
        pais_cierre_vs_media=("cierre_vs_media", "median"),
        pais_amplitud_intra=("cambio_intra", lambda c: (c > 0.03).mean() - (c < -0.03).mean()),
    ).reset_index().rename(columns={"producto": "_diario"})
    out = out.merge(region, on=key, how="left").merge(country, on=key, how="left")
    return out.drop(columns=["_diario", "_ultimo"])

