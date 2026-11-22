"""Respuesta del restaurante a la pregunta "¿te sirvió la recomendación?"."""
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.load.load_database import save_table

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


# En la nube el contenedor se reinicia con la base que trae la imagen. Las opiniones se
# copian además a un archivo en un volumen y se recuperan al arrancar.
FILE = "opiniones.jsonl"


def keep_opinion(row, folder):
    Path(folder).mkdir(parents=True, exist_ok=True)
    with open(Path(folder) / FILE, "a", encoding="utf-8") as out:
        out.write(row.to_json(orient="records", lines=True, force_ascii=False).strip() + "\n")


def restore_opinions(folder, db_path):
    path = Path(folder) / FILE
    if path.exists() and path.stat().st_size:
        save_table(pd.read_json(path, lines=True, dtype={"semana_inicio": str, "fecha": str}), "opiniones", db_path)
