"""API de AgroPrecio. Lee la base SQLite que deja el pipeline."""
import json
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.load.load_database import query

CONFIG = yaml.safe_load(open(os.getenv("AGRO_CONFIG", "config/config.yaml"), encoding="utf-8"))
DB = CONFIG["paths"]["database"]

app = FastAPI(title="AgroPrecio API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


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
