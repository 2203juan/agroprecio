"""Lista de mercado del restaurante: cuánto cuesta hoy y la próxima semana."""
import pandas as pd


def recommendation(df):
    """Lo recomendado: la clase del modelo solo cuando tuvo señal clara. Las tablas
    anteriores a la v0.8 no traen esa columna y se usa la predicción."""
    if "recomendacion" in df:
        return df["recomendacion"].fillna(df["prediccion"])
    return df["prediccion"]


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
    df["costo_recomendado"] = df["costo_proxima"].where(recommendation(df) == "baja", df["costo_hoy"])
    totals = {c: float(df[c].sum()) for c in ["costo_hoy", "costo_proxima", "costo_recomendado"]}
    return df, totals


def normalize_items(items, products):
    """Deja solo productos conocidos con cantidades positivas."""
    df = pd.DataFrame(items, columns=["producto", "kg_semana"])
    df["kg_semana"] = pd.to_numeric(df["kg_semana"], errors="coerce")
    df = df[df["producto"].isin(products) & (df["kg_semana"] > 0)]
    return df.drop_duplicates("producto", keep="last").reset_index(drop=True)


def real_savings(items, history):
    """Ahorro real de la lista con precios que ya pasaron.

    history: una fila por semana y producto con la predicción que se dio, el
    precio de esa semana (precio) y el que realmente hubo la siguiente (precio_siguiente).
    Compara tres formas de comprar la misma lista cada semana:
    - habitual: comprar todo ya, sin mirar la predicción;
    - recomendado: lo que iba a bajar se dejó para la semana siguiente;
    - ideal: pagar siempre el menor de los dos precios (sabiendo el futuro).
    El resumen separa además las compras que se aplazaron ("esperas"): la mayor parte de la
    lista se compra como siempre, así que el ahorro se concentra en esas.
    """
    empty = {"semanas": [], "resumen": None}
    if items.empty or history.empty:
        return empty
    df = history.dropna(subset=["precio_siguiente"]).merge(items, on="producto", how="inner")
    if df.empty:
        return empty
    df["costo_habitual"] = df["kg_semana"] * df["precio"]
    later = df["kg_semana"] * df["precio_siguiente"]
    df["costo_recomendado"] = later.where(recommendation(df) == "baja", df["costo_habitual"])
    df["costo_ideal"] = pd.concat([df["costo_habitual"], later], axis=1).min(axis=1)

    weeks = (df.groupby("semana_inicio", as_index=False)
             [["costo_habitual", "costo_recomendado", "costo_ideal"]].sum().round()
             .sort_values("semana_inicio"))
    weeks["ahorro"] = weeks["costo_habitual"] - weeks["costo_recomendado"]
    weeks["ahorro_acumulado"] = weeks["ahorro"].cumsum()

    # Solo las compras que se aplazaron por recomendación: ahí es donde se nota el ahorro
    waited = df[recommendation(df) == "baja"]
    waited_usual = float(waited["costo_habitual"].sum())
    waited_saving = waited_usual - float(waited["costo_recomendado"].sum())
    best = weeks.loc[weeks["ahorro"].idxmax()]

    usual, paid = float(weeks["costo_habitual"].sum()), float(weeks["costo_recomendado"].sum())
    saving, top = usual - paid, usual - float(weeks["costo_ideal"].sum())
    summary = {
        "semanas": len(weeks),
        "desde": str(weeks["semana_inicio"].min())[:10],
        "hasta": str(weeks["semana_inicio"].max())[:10],
        "costo_habitual": usual,
        "costo_recomendado": paid,
        "ahorro": saving,
        "ahorro_pct": round(saving / usual, 4) if usual else 0,
        "ahorro_por_semana": round(saving / len(weeks)),
        "ahorro_al_anio": round(saving / len(weeks) * 52),
        "semanas_con_ahorro": int((weeks["ahorro"] > 0).sum()),
        "semanas_con_perdida": int((weeks["ahorro"] < 0).sum()),
        "ahorro_maximo_posible": top,
        "parte_del_maximo": round(saving / top, 4) if top else 0,
        "esperas": len(waited),
        "esperas_acertadas": int((waited["costo_recomendado"] < waited["costo_habitual"]).sum()),
        "ahorro_en_esperas_pct": round(waited_saving / waited_usual, 4) if waited_usual else 0,
        "mejor_semana": {"semana_inicio": str(best["semana_inicio"])[:10], "ahorro": float(best["ahorro"]),
                         "ahorro_pct": round(float(best["ahorro"] / best["costo_habitual"]), 4)},
    }
    return {"semanas": weeks.to_dict("records"), "resumen": summary}
