"""Respuesta del restaurante a la pregunta "¿te sirvió la recomendación?"."""
from datetime import datetime

import pandas as pd

MAX_COMMENT = 300


def new_opinion(util, week, restaurant="", comment=""):
    return pd.DataFrame([{
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "semana_inicio": str(week)[:10],
        "restaurante": restaurant.strip(),
        "util": int(bool(util)),
        "comentario": comment.strip()[:MAX_COMMENT],
    }])


def summarize(df):
    if df.empty:
        return {"total": 0, "utiles": 0, "porcentaje_util": None}
    useful = int(df["util"].sum())
    return {"total": len(df), "utiles": useful, "porcentaje_util": round(useful / len(df), 4)}
