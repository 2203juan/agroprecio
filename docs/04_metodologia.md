# Metodología: CRISP-DM con incrementos de Scrum ML

El proyecto siguió las seis fases de CRISP-DM, organizadas en incrementos de Scrum. Cada uno terminó con una versión que funciona (MVP, Alpha, Beta, Operación y Modelo), etiquetada en git, y con una revisión de qué cambiar en la siguiente.

## Fases de CRISP-DM y dónde están en el repo

| Fase | Qué se hizo | Evidencia |
|---|---|---|
| 1. Entendimiento del negocio | Problema, usuario, propuesta de valor, OKR y KPIs | `docs/01_problema_y_kpis.md`, `docs/02_canvas.md` |
| 2. Entendimiento de los datos | Estructura del boletín SIPSA, cobertura, problemas de calidad, volatilidad en Cavasa | `notebooks/01_exploracion.ipynb`, `docs/diccionario_datos.md` |
| 3. Preparación de los datos | Descarga a bronze, limpieza a silver, variables y objetivo en gold, reglas de calidad | `src/extract`, `src/transform`, `src/quality.py` |
| 4. Modelado | Baselines, Random Forest y después un ensamble elegido con validación hacia adelante | `src/model/train.py`, `src/model/experiments.py` |
| 5. Evaluación | Métricas técnicas y de negocio (ahorro simulado) contra baselines; regla para pasar a producción | `models/registry.json`, `docs/model_card.md` |
| 6. Despliegue | API, dashboard, boletín con LLM, Docker, CI y pipeline semanal con monitoreo | `api/`, `frontend/`, `docker-compose.yml`, `.github/workflows/` |

CRISP-DM es iterativo. Las vueltas más importantes fueron:
- De preparación a entendimiento de datos: al leer todos los boletines aparecieron semanas cortas por festivos y un título con "a" en vez de "al", que rompía la lectura de la fecha.
- De entendimiento a preparación: al revisar Cavasa salieron productos repetidos dentro del mismo boletín (por ejemplo, Uva red globe nacional). Por eso se agregó la deduplicación en silver y la regla `sin_duplicados`.
- De despliegue a modelado: el monitoreo pedía reentrenar en cada corrida aunque no hubiera datos nuevos. Se agregó la condición de que existan semanas nuevas.

## Incrementos

Fue una iteración intensiva, no sprints de una semana. Las versiones v0.1 a v0.4 se construyeron el 21 de noviembre de 2026; la v0.5 y la v0.6, el 22, y comparten la etiqueta `v0.6.0`. El historial y las etiquetas de git lo muestran. Se conservó la estructura de Scrum (objetivo, historias, definición de terminado y revisión) con un incremento por versión.

### Incremento 1 · MVP (v0.1.0)

**Objetivo:** tener el precio semanal de Cavasa limpio y una primera predicción.

| Historia de usuario | Hecho cuando |
|---|---|
| Como equipo, quiero descargar todos los boletines del SIPSA sin hacerlo a mano | `download_bulletins` baja los archivos nuevos y deja `manifest.csv` |
| Como equipo, quiero una tabla limpia de precios para todo el país | `precios.parquet` en silver, con tests |
| Como restaurante, quiero saber si un producto va a subir | Baseline de persistencia funcionando |

**Revisión:** el pipeline funciona, pero sin reglas de calidad no hay forma de saber si un boletín llegó mal.

### Incremento 2 · Alpha (v0.2.0)

**Objetivo:** un modelo que le gane al baseline y algo que se pueda mostrar.

| Historia | Hecho cuando |
|---|---|
| Como equipo, quiero saber si los datos llegaron bien | 12 reglas de calidad guardadas por corrida |
| Como equipo, quiero comparar modelos de forma justa | Corte temporal y registro de versiones con métricas |
| Como restaurante, quiero ver las recomendaciones | API y dashboard en React |

**Revisión:** el modelo gana al baseline por poco (F1 0,45 contra 0,40). Se decidió no invertir más en tuning y priorizar la operación, que es lo que hace que el producto sea confiable.

### Incremento 3 · Beta (v0.3.0 y v0.4.0)

**Objetivo:** que el producto corra solo y le hable al usuario en su idioma.

| Historia | Hecho cuando |
|---|---|
| Como restaurante, quiero un mensaje corto y no una tabla | Boletín con un modelo de lenguaje y plantilla de respaldo |
| Como equipo, quiero saber si el modelo se está degradando | Acierto semanal, drift y regla de reentrenamiento |
| Como equipo, quiero que cualquiera lo pueda correr | Docker Compose, CI y pipeline semanal en GitHub Actions |

**Revisión:** el producto funciona de punta a punta. Falta la validación con restaurantes reales y el canal de WhatsApp.

### Incremento 4 · Operación (v0.5.0)

**Objetivo:** que se pueda ver, auditar y reproducir lo que pasa con los datos, el modelo y el producto.

| Historia | Hecho cuando |
|---|---|
| Como equipo, quiero comparar versiones y saber cuál está en producción | MLflow con experimentos, registro y alias `champion` |
| Como equipo, quiero enterarme de un problema sin abrir la base | Prometheus con cinco alertas y dashboard en Grafana |
| Como equipo, quiero repetir solo la etapa que falló | Pipeline por etapas y DAG en Airflow |
| Como restaurante, quiero saber si la recomendación sigue vigente | Aviso en el dashboard |
| Como equipo, quiero saber si le sirvió al restaurante | Respuesta guardada en `opiniones` y visible en Grafana |

**Revisión:** al separar el pipeline por etapas apareció un error: cada reentrenamiento reemplazaba las predicciones reales por las del backtest. Se corrigió y tiene test. La primera corrida en Airflow se quedó sin memoria en silver; leer y limpiar boletín por boletín bajó el pico de 779 a 540 MB con el mismo resultado.

### Incremento 5 · Modelo (v0.6.0)

**Objetivo:** mejorar el modelo sin engañarse con las semanas de prueba.

| Historia | Hecho cuando |
|---|---|
| Como equipo, quiero comparar variantes de forma justa | Validación en cinco bloques anteriores a la prueba, reproducible con `make experiments` |
| Como restaurante, quiero recomendaciones que ahorren más | Ahorro simulado de 0,4 % a 1,0 %, con intervalo de confianza |
| Como equipo, quiero que producción use todos los datos | Reajuste después de evaluar; las métricas siguen siendo del modelo que no vio la prueba |

**Revisión:** fue una vuelta de evaluación a preparación de datos. Al medir con intervalos se vio que la ventaja de la v0.5 no era segura, y lo que más ayudó fueron variables y datos, no el algoritmo. Ver [experimentos](09_experimentos.md).

## Definición de terminado

- El código tiene tests o se verificó corriendo el pipeline completo.
- El pipeline corre de punta a punta con `python main.py --sin-descarga`.
- Las reglas de calidad pasan.
- La documentación del cambio está en `docs/` o en el README.

## Backlog para la siguiente versión

1. Validar con 5 a 10 restaurantes y medir el ahorro real ([plan](07_validacion.md)).
2. Enviar el boletín por WhatsApp.
3. Sumar clima del IDEAM, y abastecimiento (hoja 1.10) cuando haya historia suficiente.
4. Volver a evaluar con semanas nuevas, que ningún modelo haya visto.
5. Pasar SQLite a Postgres si hay más de una ciudad.
