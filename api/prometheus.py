"""Métricas para Prometheus: tráfico de la API y estado del producto.

El estado (modelo, monitoreo, calidad, boletines, opiniones) se lee de la base y de los
logs en cada consulta, porque lo escribe el pipeline y no la API.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from prometheus_client import Counter, Histogram
from prometheus_client.core import GaugeMetricFamily

from src.load.load_database import read_table
from src.opiniones import summarize
from src.vigencia import freshness

REQUESTS = Counter("agroprecio_http_peticiones_total", "Peticiones a la API", ["ruta", "metodo", "codigo"])
LATENCY = Histogram("agroprecio_http_latencia_segundos", "Latencia de la API", ["ruta"],
                    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5))


async def track_requests(request, call_next):
    start, code = time.perf_counter(), 500
    try:
        response = await call_next(request)
        code = response.status_code
        return response
    finally:
        # La plantilla de la ruta, no la URL, para no crear una serie por producto
        route = getattr(request.scope.get("route"), "path", "otra")
        REQUESTS.labels(route, request.method, code).inc()
        LATENCY.labels(route).observe(time.perf_counter() - start)


def gauge(name, text, values, labels=()):
    """values: {(etiquetas): número}. Los None se omiten."""
    metric = GaugeMetricFamily(f"agroprecio_{name}", text, labels=list(labels))
    for key, value in values.items():
        if value is not None and value == value:
            metric.add_metric([str(k) for k in key], float(value))
    return metric


class ProductCollector:
    def __init__(self, cfg):
        self.db = cfg["paths"]["database"]
        self.registry = Path(cfg["paths"]["models"]) / "registry.json"
        self.llm_log = Path(cfg["paths"]["logs"]) / "llm.jsonl"

    def describe(self):
        return []

    def collect(self):
        yield from self.model()
        yield from self.monitoring()
        yield from self.data()
        yield from self.llm()
        yield gauge("opiniones", "Respuestas a ¿te sirvió?", self.opinions(), ["respuesta"])

    def model(self):
        registry = json.loads(self.registry.read_text()) if self.registry.exists() else []
        prod = [r for r in registry if r["estado"] == "produccion"]
        values = {}
        if prod:
            for name, metrics in prod[-1]["metricas"].items():
                for metric in ("accuracy", "f1_macro", "ahorro_simulado"):
                    values[(name, metric)] = metrics.get(metric)
        yield gauge("modelo_metrica", "Métricas de prueba del modelo en producción y los baselines",
                    values, ["evaluado", "metrica"])
        yield gauge("modelo_versiones", "Versiones en el registro", {(): len(registry)})

    def monitoring(self):
        df = read_table("monitoreo", self.db)
        last = df.iloc[-1].to_dict() if len(df) else {}
        for column, name, text in [
            ("accuracy_ultimas_8_semanas", "accuracy_8_semanas", "Acierto de 8 semanas, con backtest"),
            ("accuracy_real", "accuracy_real", "Acierto de predicciones hechas antes del resultado"),
            ("predicciones_reales", "predicciones_reales", "Predicciones reales con resultado"),
            ("productos_con_drift", "productos_con_drift", "Productos con un cambio de precio atípico"),
            ("requiere_reentrenar", "requiere_reentrenar", "1 si el monitoreo pide reentrenar"),
        ]:
            yield gauge(name, text, {(): last.get(column)})
        stamp = datetime.fromisoformat(last["fecha"]).timestamp() if last else None
        yield gauge("ultima_corrida_timestamp", "Última corrida del pipeline", {(): stamp})

    def data(self):
        quality = read_table("calidad_datos", self.db)
        values = {}
        if len(quality):
            run = quality[quality["fecha"] == quality["fecha"].max()]
            ok = int(run["ok"].sum())
            values = {("ok",): ok, ("falla",): len(run) - ok}
        yield gauge("reglas_calidad", "Reglas de calidad de la última corrida", values, ["estado"])

        alerts = read_table("alertas", self.db)
        counts = alerts["prediccion"].value_counts().to_dict() if len(alerts) else {}
        yield gauge("alertas", "Productos por predicción", {(k,): v for k, v in counts.items()}, ["prediccion"])
        fresh = freshness(alerts["semana_inicio"].iloc[0]) if len(alerts) else {}
        yield gauge("dias_desde_boletin", "Días desde el fin del último boletín",
                    {(): fresh.get("dias_desde_boletin")})
        yield gauge("recomendacion_vencida", "1 si la semana recomendada ya pasó", {(): fresh.get("vencida")})

    def llm(self):
        lines = self.llm_log.read_text(encoding="utf-8").splitlines() if self.llm_log.exists() else []
        records = [json.loads(line) for line in lines if line.strip()]
        sources = {("llm",): 0, ("plantilla",): 0}
        for r in records:
            sources[(r["fuente"],)] = sources.get((r["fuente"],), 0) + 1
        yield gauge("boletines", "Boletines generados por fuente", sources, ["fuente"])
        yield gauge("llm_tokens", "Tokens del modelo de lenguaje acumulados", {
            ("entrada",): sum(r.get("tokens_entrada", 0) for r in records),
            ("salida",): sum(r.get("tokens_salida", 0) for r in records)}, ["tipo"])
        yield gauge("llm_descartados", "Boletines descartados por cifras inventadas",
                    {(): sum("descartado" in r for r in records)})
        yield gauge("llm_errores", "Llamadas al modelo de lenguaje con error", {(): sum("error" in r for r in records)})

    def opinions(self):
        s = summarize(read_table("opiniones", self.db))
        return {("util",): s["utiles"], ("no_util",): s["total"] - s["utiles"]}
