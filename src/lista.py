"""Lista de mercado del restaurante: cuánto cuesta hoy y la próxima semana."""
import pandas as pd


def cost_list(items, alerts):
    """items: producto y kg_semana. alerts: predicciones con rango esperado.

    Siguiendo la recomendación: lo que sube se compra hoy, lo que baja
    se compra la próxima semana y lo estable se compra como siempre (hoy).
    """
    if items.empty:
        return items, {"costo_hoy": 0, "costo_proxima": 0, "costo_recomendado": 0}
    df = items.merge(alerts, on="producto", how="inner")
    expected = (df["precio_min_esperado"] + df["precio_max_esperado"]) / 2
    df["costo_hoy"] = (df["kg_semana"] * df["precio"]).round()
    df["costo_proxima"] = (df["kg_semana"] * expected).round()
    df["costo_recomendado"] = df["costo_proxima"].where(df["prediccion"] == "baja", df["costo_hoy"])
    totals = {c: float(df[c].sum()) for c in ["costo_hoy", "costo_proxima", "costo_recomendado"]}
    return df, totals


def normalize_items(items, products):
    """Deja solo productos conocidos con cantidades positivas."""
    df = pd.DataFrame(items, columns=["producto", "kg_semana"])
    df["kg_semana"] = pd.to_numeric(df["kg_semana"], errors="coerce")
    df = df[df["producto"].isin(products) & (df["kg_semana"] > 0)]
    return df.drop_duplicates("producto", keep="last").reset_index(drop=True)
