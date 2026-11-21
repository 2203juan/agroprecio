# Operación: DataOps, MLOps y LLMOps

## Flujo semanal

```
Viernes      DANE publica el boletín
Sábado 8am   GitHub Actions corre pipeline_semanal.yml
             ├─ restaura data/ y models/ de la corrida anterior
             ├─ descarga solo los boletines nuevos (bronze)
             ├─ limpia, valida y construye silver y gold
             ├─ si el monitoreo lo pidió y hay datos nuevos: reentrena
             ├─ predice la semana y guarda alertas
             ├─ calcula acierto y drift
             ├─ genera el boletín con Claude
             └─ publica la base, el registro y los logs como artefactos
```

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
| Versionado de modelos | Cada entrenamiento guarda `models/vAAAAMMDD_HHMMSS.joblib` |
| Registro | `models/registry.json`: versión, fecha, rango de datos, variables, parámetros, métricas y estado (`produccion`, `archivado`, `rechazado`) |
| Regla de promoción | Un modelo pasa a producción solo si le gana al baseline en F1 y tiene accuracy ≥ 0,40 |
| Validación temporal | Siempre se prueba con las últimas 20 semanas, nunca con datos mezclados al azar |
| Registro de predicciones | Tabla `predicciones` con versión del modelo y fecha |
| Monitoreo de desempeño | Se cruza cada predicción con lo que pasó; acierto semanal en `accuracy_semanal` |
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
| Observabilidad | `logs/llm.jsonl`: prompt, respuesta, modelo, tokens, latencia, stop_reason y si se descartó |
| Costo controlado | Una llamada por semana, esfuerzo `low` |

## CI/CD

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `ci.yml` | Cada push a `main` y cada pull request | Instala dependencias, corre `pytest` y construye las imágenes de Docker |
| `pipeline_semanal.yml` | Sábados 8:00 a.m. (hora Colombia) o a mano | Corre el pipeline con el estado anterior y publica los resultados |

## Docker

| Servicio | Imagen | Qué hace |
|---|---|---|
| `pipeline` | `Dockerfile` (Python 3.12) | Corre `main.py` y termina |
| `api` | La misma imagen | `uvicorn` en el puerto 8000; arranca cuando el pipeline termina bien |
| `web` | `frontend/Dockerfile` (Node para compilar, Nginx para servir) | Dashboard en el puerto 8080; Nginx redirige `/api` al servicio `api` |

`data/`, `models/` y `logs/` se montan como volúmenes, así que el estado se conserva entre corridas.
