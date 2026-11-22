"""API de AgroPrecio. Lee la base SQLite que deja el pipeline."""
import json
import os
from pathlib import Path

import yaml
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

from api import actualizar
from api.prometheus import ProductCollector, track_requests
from src.lista import cost_list, normalize_items
from src.model.metrics import classification_metrics, evaluate_version
from src.model.train import evaluated_model
from src.load.load_database import query, read_table, save_table
from src.opiniones import MAX_COMMENT, new_opinion, summarize
from src.vigencia import freshness

CONFIG = yaml.safe_load(open(os.getenv("AGRO_CONFIG", "config/config.yaml"), encoding="utf-8"))
DB = CONFIG["paths"]["database"]

app = FastAPI(title="AgroPrecio API", version="0.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "PUT"], allow_headers=["*"])
app.middleware("http")(track_requests)
COLLECTOR = ProductCollector(CONFIG)
REGISTRY.register(COLLECTOR)


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


@app.get("/vigencia")
def validity():
    df = read_table("alertas", DB)
    if df.empty:
        raise HTTPException(404, "Todavía no hay alertas")
    return freshness(df["semana_inicio"].iloc[0])


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
        "opiniones": summarize(read_table("opiniones", DB)),
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


# ---------- ¿Te sirvió? ----------

class Opinion(BaseModel):
    util: bool
    restaurante: str = Field(default="", max_length=80)
    comentario: str = Field(default="", max_length=MAX_COMMENT)


@app.get("/opiniones")
def get_opinions():
    return summarize(read_table("opiniones", DB))


@app.post("/opiniones", status_code=201)
def post_opinion(opinion: Opinion):
    alerts = read_table("alertas", DB)
    if alerts.empty:
        raise HTTPException(404, "Todavía no hay una recomendación para calificar")
    row = new_opinion(opinion.util, alerts["semana_inicio"].iloc[0], opinion.restaurante, opinion.comentario)
    save_table(row, "opiniones", DB, mode="append")
    return get_opinions()


# ---------- Actualizar con el boletín más reciente del DANE ----------

@app.post("/actualizar")
def update():
    started = actualizar.start()
    return {"iniciado": started, **actualizar.status()}


@app.get("/actualizar")
def update_status():
    return actualizar.status()


# ---------- Métricas de los modelos ----------

def live_metrics():
    """Predicciones reales de producción (no backtest) que ya tienen resultado."""
    df = query(
        "SELECT p.modelo_version AS version, p.prediccion, f.clase FROM predicciones p "
        "JOIN features f ON f.producto = p.producto AND f.semana_inicio = p.semana_inicio "
        "WHERE p.confianza IS NOT NULL AND f.clase IS NOT NULL", DB)
    return [{"version": v, **classification_metrics(g["clase"], g["prediccion"])}
            for v, g in df.groupby("version")]


@app.get("/metrics")
def metrics(formato: str = "json"):
    """Tabla de métricas de cada versión del modelo frente a los baselines,
    sobre su periodo de prueba. Con ?formato=html se ve como tabla en el navegador."""
    path = Path(CONFIG["paths"]["models"]) / "registry.json"
    registry = json.loads(path.read_text()) if path.exists() else []
    gold = read_table("features", DB)
    gold["semana_inicio"] = pd.to_datetime(gold["semana_inicio"])

    table, detail = [], {}
    for entry in registry:
        model = evaluated_model(CONFIG["paths"]["models"], entry["version"])
        if model is None:
            continue
        rows, classes, cm = evaluate_version(model, entry, gold, CONFIG)
        table += rows
        detail[entry["version"]] = {"por_clase": records(classes), "matriz_confusion": cm}

    live = live_metrics()
    if formato == "html":
        return HTMLResponse(metrics_html(table, live))
    return {"tabla": table, "detalle_modelo": detail, "en_produccion": live}


@app.get("/prometheus", include_in_schema=False)
def prometheus():
    """Métricas en el formato de Prometheus (la tabla de /metrics es para personas)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def metrics_html(table, live):
    style = ("<style>body{font-family:system-ui;margin:24px;color:#2b2118;background:#fbf3e1}"
             "table{border-collapse:collapse;font-size:13px;margin-bottom:24px}"
             "th,td{border:1px solid #ecdfc4;padding:4px 8px;text-align:right}"
             "th{background:#2e7d32;color:#fff}td:nth-child(-n+3){text-align:left}</style>")
    live_html = pd.DataFrame(live).to_html(index=False, na_rep="–") if live else \
        "<p>Todavía no hay predicciones de producción con resultado real.</p>"
    return (f"<html><head><meta charset='utf-8'><title>Métricas AgroPrecio</title>{style}</head><body>"
            "<h2>Métricas por versión (periodo de prueba)</h2>"
            f"{pd.DataFrame(table).to_html(index=False, na_rep='–')}"
            f"<h2>Métricas en producción</h2>{live_html}</body></html>")
