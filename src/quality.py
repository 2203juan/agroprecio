"""Reglas de calidad de datos. Se corren en cada ejecución del pipeline
y el resultado queda guardado en la tabla calidad_datos."""
from datetime import datetime

import pandas as pd

# Si falla alguna de estas, el pipeline se detiene antes de entrenar o publicar
CRITICAL = {"sin_nulos_en_llaves", "precios_positivos"}


def check_silver(df):
    weeks = df["semana_inicio"].drop_duplicates().sort_values()
    gaps = weeks.diff().dt.days.dropna()
    checks = [
        ("sin_nulos_en_llaves", df[["semana_inicio", "producto", "mercado"]].notna().all().all()),
        ("precios_positivos", bool((df["precio_medio"] > 0).all())),
        ("min_menor_o_igual_max", bool((df["precio_min"] <= df["precio_max"]).all())),
        ("medio_entre_min_y_max", bool(((df["precio_medio"] >= df["precio_min"] - 1) &
                                       (df["precio_medio"] <= df["precio_max"] + 1)).all())),
        ("sin_duplicados", not df.duplicated(["semana_inicio", "producto", "mercado"]).any()),
        ("semanas_de_7_dias", bool((gaps % 7 == 0).all())),
        ("minimo_10_semanas", len(weeks) >= 10),
    ]
    return to_frame("silver", checks, len(df))


def check_gold(df, products):
    found = set(df["producto"].unique())
    checks = [
        ("todos_los_productos_presentes", set(products) <= found),
        ("sin_nulos_en_precio", bool(df["precio"].notna().all())),
        ("una_fila_por_producto_y_semana", not df.duplicated(["producto", "semana_inicio"]).any()),
        ("clases_validas", bool(df["clase"].dropna().isin(["sube", "baja", "estable"]).all())),
    ]
    return to_frame("gold", checks, len(df))


def to_frame(layer, checks, rows):
    now = datetime.now().isoformat(timespec="seconds")
    return pd.DataFrame([
        {"fecha": now, "capa": layer, "regla": name, "ok": bool(ok), "filas": rows}
        for name, ok in checks
    ])
