# Operación: DataOps, MLOps y LLMOps

## Flujo semanal

```
Viernes             DANE publica el boletín (a veces con rezago)
Mié y sáb 8 a.m.    GitHub Actions corre pipeline_semanal.yml
             (en un despliegue propio: Airflow a las 7 a.m., la API los sábados o el botón "Buscar boletín nuevo")
             ├─ restaura data/ y models/ de la corrida anterior
             ├─ descarga solo los boletines nuevos (bronze)
             ├─ limpia, valida y construye silver y gold
             ├─ si el monitoreo lo pidió y hay datos nuevos: reentrena
             ├─ predice la semana y guarda alertas
             ├─ copia a MLflow las versiones nuevas del modelo (si hay servidor)
             ├─ calcula acierto y drift
             ├─ genera el boletín con Claude
             └─ publica la base, el registro y los logs como artefactos
```

En un despliegue con Docker, la API también corre el pipeline: con el botón *Buscar boletín nuevo* del dashboard (`POST /actualizar`, el progreso se consulta con `GET /actualizar` y queda en `logs/actualizacion.log`) y de forma automática cada sábado a las 8 a.m., salvo que ese día ya haya corrido. El día y la hora están en `update` dentro de `config/config.yaml`. Solo puede haber una actualización a la vez.

## DataOps

| Práctica | Implementación |
|---|---|
| Trazabilidad del dato crudo | `data/bronze/manifest.csv` guarda el id del documento, título, URL, tamaño y fecha de descarga de cada Excel |
| Descarga incremental | Solo se bajan los boletines que no están en bronze |
| Datos inmutables en bronze | Los Excel no se modifican; toda limpieza pasa a silver |
| Calidad automática | 11 reglas en `src/quality.py` (nulos, precios positivos, mínimo ≤ máximo, duplicados, semanas de 7 días, productos presentes, clases válidas…) |
| Historial de calidad | Cada corrida agrega sus resultados a la tabla `calidad_datos` |
| Freno de emergencia | Si fallan las reglas críticas, el pipeline se detiene antes de entrenar o publicar |
| Configuración separada del código | Mercado, productos, umbrales y rutas en `config/config.yaml` |

## MLOps

| Práctica | Implementación |
|---|---|
| Tabla de métricas | `GET /metrics` re-evalúa cada versión del registro y los baselines sobre el mismo periodo de prueba (accuracy, balanced accuracy, precision, recall, F1, kappa, MCC, log loss, ROC AUC, ahorro), con métricas por clase, matriz de confusión y métricas en producción |
| Versionado de modelos | Cada entrenamiento guarda dos archivos: `v…_prueba.joblib`, con el que se miden las métricas, y `v….joblib`, reajustado con todos los datos, que va a producción |
| Comparación de variantes | `make experiments`, con validación hacia adelante; se registra en el experimento `agroprecio-comparacion` |
| Registro | `models/registry.json`: versión, fecha, rango de datos, variables, parámetros, métricas y estado (`produccion`, `archivado`, `rechazado`) |
| Regla de promoción | Un modelo pasa a producción solo si le gana al baseline en F1 y tiene accuracy ≥ 0,40 |
| Validación temporal | Siempre se prueba con las últimas 20 semanas, nunca con datos mezclados al azar |
| Registro de predicciones | Tabla `predicciones` con versión del modelo y fecha |
| Monitoreo de desempeño | Se cruza cada predicción con lo que pasó; acierto semanal en `accuracy_semanal`. El acierto real (`accuracy_real`) excluye el backtest |
| Historial protegido | Un reentrenamiento no pisa las predicciones reales con las del backtest |
| Monitoreo de datos | Drift por producto (z-score del cambio semanal > 3) en la tabla `drift` |
| Reentrenamiento | Si el acierto de las últimas 8 semanas baja de 0,40 o más del 30 % de los productos tiene drift, y hay semanas nuevas, el siguiente run reentrena |
| Reproducibilidad | `requirements.txt` con versiones fijas, semilla fija y Docker |

## LLMOps

| Práctica | Implementación |
|---|---|
| Prompt versionado en el código | `SYSTEM` en `src/llm/boletin.py` |
| Datos estructurados al modelo | El prompt lleva un JSON con producto, precio, cambio, predicción y confianza |
| Guardrail de cifras | `numbers_are_grounded` descarta el texto si aparece un precio que no está en los datos |
| Respaldo | Sin API key, con error o con texto descartado, se usa una plantilla |
| Trazas | Con MLflow encendido, cada boletín queda como traza en el experimento `agroprecio-boletin` |
| Observabilidad | `logs/llm.jsonl`: prompt, respuesta, modelo, tokens, latencia, stop_reason y si se descartó |
| Costo controlado | Una llamada por semana, esfuerzo `low` |

## MLflow

`models/registry.json` decide qué modelo está en producción; MLflow recibe una copia de cada versión. Así el pipeline corre igual en GitHub Actions, donde no hay servidor, y si MLflow se cae la siguiente corrida lo pone al día.

| Qué | Dónde |
|---|---|
| Parámetros y métricas de cada versión y de los baselines | Experimento `agroprecio` |
| Modelo y alias `champion` | Registro, `agroprecio-precios-cavasa` |
| Boletines | Experimento `agroprecio-boletin`, pestaña *Traces* |
| Variantes comparadas | Experimento `agroprecio-comparacion` |

## Prometheus y Grafana

La API publica `/prometheus`. Son dos tipos de métricas: el tráfico (peticiones y latencia por ruta) y el estado del producto, que se lee de la base en cada consulta. `/metrics` sigue siendo la tabla para personas.

| Alerta | Cuándo |
|---|---|
| `ApiCaida` | La API no responde por 2 minutos |
| `ReglasDeCalidadFallan` | Alguna regla falló en la última corrida |
| `ModeloPideReentrenar` | Acierto bajo el mínimo o drift |
| `RecomendacionVencida` | La semana recomendada ya pasó |
| `PipelineSinCorrer` | Más de 8 días sin correr |

Las alertas se ven en Prometheus; todavía no se envían por correo ni por chat.

## Airflow

El DAG `agroprecio_semanal` corre una tarea por etapa: `descargar → silver → gold → calidad → modelo → prediccion → boletin`. Cada tarea ejecuta `python main.py --etapa <nombre>` en un entorno propio, separado del de Airflow.

Es opcional. Convive con las otras dos formas de programarlo: la API no corre si ese día ya hubo una corrida. No se debe disparar el DAG mientras corre el botón *Buscar boletín nuevo*, porque ambos escriben la misma base.

## CI/CD

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `ci.yml` | Cada push a `main` y cada pull request | Instala dependencias, corre `pytest`, construye las imágenes de Docker y revisa que el DAG cargue |
| `pipeline_semanal.yml` | Miércoles y sábados 8:00 a.m. (hora Colombia) o a mano | Corre el pipeline con el estado anterior y publica los resultados |

## Docker

| Servicio | Imagen | Qué hace |
|---|---|---|
| `pipeline` | `Dockerfile` (Python 3.12) | Corre `main.py` y termina |
| `api` | La misma imagen | `uvicorn` en el puerto 8000; arranca cuando el pipeline termina bien |
| `web` | `frontend/Dockerfile` (Node para compilar, Nginx para servir) | Dashboard en el puerto 8080; Nginx redirige `/api` al servicio `api` |

| `mlflow` | `docker/mlflow` | Experimentos, registro de modelos y trazas, puerto 5002 |
| `prometheus` | `prom/prometheus` | Lee `/prometheus` de la API cada 15 s y evalúa las alertas, puerto 9092 |
| `grafana` | `grafana/grafana` | Dashboard precargado, puerto 3002 |
| `airflow` | `docker/airflow` | Opcional (`make airflow`), puerto 8082 |

Todos los puertos se cambian en `.env`. Los de MLflow, Prometheus, Grafana y Airflow solo se abren en el mismo equipo, porque Grafana se puede ver sin cuenta y Airflow no pide usuario.

`data/`, `models/` y `logs/` se montan como volúmenes, así que el estado se conserva entre corridas.
