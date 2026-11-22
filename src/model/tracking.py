"""Seguimiento en MLflow: experimentos, registro de modelos y trazas del LLM.

Es opcional. Sin MLFLOW_TRACKING_URI, o si el servidor no responde, el pipeline sigue
igual. La fuente de verdad de qué modelo está en producción es models/registry.json;
MLflow recibe una copia de cada versión, así que cada corrida se pone al día sola.
"""
import json
import os
from contextlib import contextmanager
from pathlib import Path

# Con el servidor caído, fallar rápido en vez de reintentar durante minutos
os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "1")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "20")
# Menos ruido en los logs: en el contenedor no hay git
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

EXPERIMENT = "agroprecio"
LLM_EXPERIMENT = "agroprecio-boletin"
MODEL_NAME = "agroprecio-precios-cavasa"
ALIAS = "champion"
COMPARISON_EXPERIMENT = "agroprecio-comparacion"


def enabled():
    return bool(os.getenv("MLFLOW_TRACKING_URI"))


def flat_metrics(entry):
    """{'modelo': {'f1_macro': 0.4}} -> {'modelo_f1_macro': 0.4}, solo números."""
    return {
        f"{name}_{metric}": float(value)
        for name, metrics in entry["metricas"].items()
        for metric, value in metrics.items()
        if isinstance(value, (int, float))
    }


def run_params(entry, cfg):
    params = {k: v for k, v in entry["parametros"].items() if isinstance(v, (str, int, float))}
    params.update({f"datos_{k}": v for k, v in entry["datos"].items()})
    params["umbral"] = cfg["model"]["threshold"]
    params["semanas_prueba"] = cfg["model"]["test_weeks"]
    return params


def log_version(mlflow, entry, cfg):
    import joblib

    models_dir = Path(cfg["paths"]["models"])
    with mlflow.start_run(run_name=entry["version"], tags={"version": entry["version"]}):
        mlflow.log_params(run_params(entry, cfg))
        mlflow.log_metrics(flat_metrics(entry))
        mlflow.log_dict(entry, "registro.json")
        mlflow.log_dict({"variables": entry["features"]}, "variables.json")
        # El modelo se guarda con cloudpickle, igual que el .joblib de models/
        info = mlflow.sklearn.log_model(
            joblib.load(models_dir / f"{entry['version']}.joblib"), name="modelo",
            serialization_format="cloudpickle", pip_requirements=["scikit-learn", "pandas"],
        )
    return mlflow.register_model(info.model_uri, MODEL_NAME, tags={"version": entry["version"]}).version


def sync_registry(cfg, logger):
    """Copia a MLflow las versiones de models/registry.json que todavía no estén
    y deja el alias champion en la que está en producción."""
    path = Path(cfg["paths"]["models"]) / "registry.json"
    if not enabled() or not path.exists():
        return 0
    try:
        import mlflow
        import mlflow.sklearn

        mlflow.set_experiment(EXPERIMENT)
        client = mlflow.MlflowClient()
        known = {v.tags.get("version"): v.version
                 for v in client.search_model_versions(f"name='{MODEL_NAME}'")}
        new = 0
        for entry in json.loads(path.read_text()):
            file = path.parent / f"{entry['version']}.joblib"
            if entry["version"] not in known and file.exists():
                known[entry["version"]] = log_version(mlflow, entry, cfg)
                new += 1
            if entry["version"] in known:
                client.set_model_version_tag(MODEL_NAME, known[entry["version"]], "estado", entry["estado"])
                if entry["estado"] == "produccion":
                    client.set_registered_model_alias(MODEL_NAME, ALIAS, known[entry["version"]])
        logger.info("MLflow: %s versiones nuevas registradas", new)
        return new
    except Exception as e:
        logger.warning("No se pudo registrar en MLflow, el pipeline sigue: %s", str(e)[:200])
        return 0


def log_comparison(table, logger):
    """Una corrida por variante probada en src/model/experiments.py."""
    if not enabled():
        return
    try:
        import mlflow

        mlflow.set_experiment(COMPARISON_EXPERIMENT)
        for row in table.to_dict("records"):
            with mlflow.start_run(run_name=row["variante"]):
                mlflow.log_metrics({k: v for k, v in row.items() if k != "variante"})
    except Exception as e:
        logger.warning("No se pudo registrar la comparación en MLflow: %s", str(e)[:200])


class _NoSpan:
    def set_inputs(self, *_): ...
    def set_outputs(self, *_): ...
    def set_attributes(self, *_): ...


@contextmanager
def llm_span(name, logger, span_type="CHAIN"):
    """Span de MLflow para las llamadas al LLM; no hace nada si MLflow no está disponible."""
    span = None
    if enabled():
        try:
            import mlflow

            mlflow.set_experiment(LLM_EXPERIMENT)
            span = mlflow.start_span(name=name, span_type=span_type)
        except Exception as e:
            logger.warning("Sin traza en MLflow: %s", str(e)[:200])
            span = None
    if span is None:
        yield _NoSpan()
    else:
        with span as active:
            yield active
