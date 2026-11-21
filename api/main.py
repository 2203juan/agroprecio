"""API de AgroPrecio. Lee la base SQLite que deja el pipeline."""
import json
import os
from pathlib import Path

import yaml
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api import actualizar
from src.lista import cost_list, normalize_items
from src.load.load_database import query, read_table, save_table

CONFIG = yaml.safe_load(open(os.getenv("AGRO_CONFIG", "config/config.yaml"), encoding="utf-8"))
DB = CONFIG["paths"]["database"]

app = FastAPI(title="AgroPrecio API", version="0.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "PUT"], allow_headers=["*"])



def last_run():
    df = read_table("monitoreo", DB)
    return df["fecha"].max()[:10] if len(df) else None


if CONFIG.get("update", {}).get("auto"):
    actualizar.schedule(CONFIG["update"]["weekday"], CONFIG["update"]["hour"], last_run)


def records(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))


@app.get("/salud")
def health():
    return {"estado": "ok", "base_de_datos": Path(DB).exists()}


@app.get("/productos")
def products():
    return CONFIG["products"]


@app.get("/alertas")
def alerts():
    return records(query("SELECT * FROM alertas", DB))


@app.get("/historico/{producto}")
def history(producto: str, semanas: int = 52):
    df = query(
        "SELECT semana_inicio, precio, precio_nacional FROM features "
        "WHERE producto = ? ORDER BY semana_inicio DESC LIMIT ?",
        DB, (producto, semanas),
    )
    if df.empty:
        raise HTTPException(404, f"No hay datos para {producto}")
    return records(df.iloc[::-1])


@app.get("/boletin")
def bulletin():
    df = query("SELECT * FROM boletines ORDER BY fecha DESC LIMIT 1", DB)
    return records(df)[0] if len(df) else {}


@app.get("/modelo")
def model():
    path = Path(CONFIG["paths"]["models"]) / "registry.json"
    registry = json.loads(path.read_text()) if path.exists() else []
    prod = [r for r in registry if r["estado"] == "produccion"]
    return {"produccion": prod[-1] if prod else None, "versiones": len(registry)}


@app.get("/monitoreo")
def monitoring():
    return {
        "estado": records(query("SELECT * FROM monitoreo ORDER BY fecha DESC LIMIT 1", DB)),
        "accuracy_semanal": records(query("SELECT * FROM accuracy_semanal", DB)),
        "drift": records(query("SELECT * FROM drift", DB)),
        "calidad": records(query(
            "SELECT * FROM calidad_datos WHERE fecha = (SELECT MAX(fecha) FROM calidad_datos)", DB)),
    }


# ---------- Lista de mercado del restaurante ----------

class Item(BaseModel):
    producto: str
    kg_semana: float


class Lista(BaseModel):
    restaurante: str = "Mi restaurante"
    items: list[Item]


def read_list():
    df = read_table("listas", DB)
    name = df["restaurante"].iloc[0] if len(df) else "Mi restaurante"
    return name, df[["producto", "kg_semana"]] if len(df) else pd.DataFrame(columns=["producto", "kg_semana"])


@app.get("/lista")
def get_list():
    name, items = read_list()
    rows, totals = cost_list(items, query("SELECT * FROM alertas", DB))
    return {"restaurante": name, "items": records(rows), "totales": totals}


@app.put("/lista")
def put_list(lista: Lista):
    items = normalize_items([i.model_dump() for i in lista.items], CONFIG["products"])
    save_table(items.assign(restaurante=lista.restaurante.strip() or "Mi restaurante"), "listas", DB)
    return get_list()


# ---------- Actualizar con el boletín más reciente del DANE ----------

@app.post("/actualizar")
def update():
    started = actualizar.start()
    return {"iniciado": started, **actualizar.status()}


@app.get("/actualizar")
def update_status():
    return actualizar.status()
