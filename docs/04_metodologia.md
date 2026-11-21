# Metodología: CRISP-DM con sprints de Scrum ML

El proyecto siguió las seis fases de CRISP-DM, organizadas en tres sprints cortos de Scrum. Cada sprint terminó con una versión que funciona (MVP, Alpha y Beta) y con una revisión de qué cambiar en el siguiente.

## Fases de CRISP-DM y dónde están en el repo

| Fase | Qué se hizo | Evidencia |
|---|---|---|
| 1. Entendimiento del negocio | Problema, usuario, propuesta de valor, OKR y KPIs | `docs/01_problema_y_kpis.md`, `docs/02_canvas.md` |
| 2. Entendimiento de los datos | Estructura del boletín SIPSA, cobertura, problemas de calidad, volatilidad en Cavasa | `notebooks/01_exploracion.ipynb`, `docs/diccionario_datos.md` |
| 3. Preparación de los datos | Descarga a bronze, limpieza a silver, variables y objetivo en gold, reglas de calidad | `src/extract`, `src/transform`, `src/quality.py` |
| 4. Modelado | Baselines, Random Forest con corte temporal | `src/model/train.py` |
| 5. Evaluación | Métricas técnicas y de negocio (ahorro simulado) contra baselines; regla para pasar a producción | `models/registry.json`, `docs/model_card.md` |
| 6. Despliegue | API, dashboard, boletín con LLM, Docker, CI y pipeline semanal con monitoreo | `api/`, `frontend/`, `docker-compose.yml`, `.github/workflows/` |

CRISP-DM es iterativo. Las vueltas más importantes fueron:
- De preparación a entendimiento de datos: al leer todos los boletines aparecieron semanas cortas por festivos y un título con "a" en vez de "al", que rompía la lectura de la fecha.
- De entendimiento a preparación: al revisar Cavasa salieron productos repetidos dentro del mismo boletín (por ejemplo, Uva red globe nacional). Por eso se agregó la deduplicación en silver y la regla `sin_duplicados`.
- De despliegue a modelado: el monitoreo pedía reentrenar en cada corrida aunque no hubiera datos nuevos. Se agregó la condición de que existan semanas nuevas.

## Sprints

Duración total: dos semanas. Un sprint por versión del producto.

### Sprint 1 · MVP (días 1 a 4)

**Objetivo:** tener el precio semanal de Cavasa limpio y una primera predicción.

| Historia de usuario | Hecho cuando |
|---|---|
| Como equipo, quiero descargar todos los boletines del SIPSA sin hacerlo a mano | `download_bulletins` baja los archivos nuevos y deja `manifest.csv` |
| Como equipo, quiero una tabla limpia de precios para todo el país | `precios.parquet` en silver, con tests |
| Como restaurante, quiero saber si un producto va a subir | Baseline de persistencia funcionando |

**Revisión:** el pipeline funciona, pero sin reglas de calidad no hay forma de saber si un boletín llegó mal.

### Sprint 2 · Alpha (días 5 a 9)

**Objetivo:** un modelo que le gane al baseline y algo que se pueda mostrar.

| Historia | Hecho cuando |
|---|---|
| Como equipo, quiero saber si los datos llegaron bien | 11 reglas de calidad guardadas por corrida |
| Como equipo, quiero comparar modelos de forma justa | Corte temporal y registro de versiones con métricas |
| Como restaurante, quiero ver las recomendaciones | API y dashboard en React |

**Revisión:** el modelo gana al baseline por poco (F1 0,45 contra 0,40). Se decidió no invertir más en tuning y priorizar la operación, que es lo que hace que el producto sea confiable.

### Sprint 3 · Beta (días 10 a 14)

**Objetivo:** que el producto corra solo y le hable al usuario en su idioma.

| Historia | Hecho cuando |
|---|---|
| Como restaurante, quiero un mensaje corto y no una tabla | Boletín con Claude y plantilla de respaldo |
| Como equipo, quiero saber si el modelo se está degradando | Acierto semanal, drift y regla de reentrenamiento |
| Como equipo, quiero que cualquiera lo pueda correr | Docker Compose, CI y pipeline semanal en GitHub Actions |

**Revisión:** el producto funciona de punta a punta. Falta la validación con restaurantes reales y el canal de WhatsApp.

## Definición de terminado

- El código tiene tests o se verificó corriendo el pipeline completo.
- El pipeline corre de punta a punta con `python main.py --sin-descarga`.
- Las reglas de calidad pasan.
- La documentación del cambio está en `docs/` o en el README.

## Backlog para la siguiente versión

1. Validar con 5 a 10 restaurantes y medir el ahorro real.
2. Enviar el boletín por WhatsApp.
3. Sumar abastecimiento (hoja 1.10) y clima del IDEAM como variables.
4. Usar también la predicción "baja" en la estrategia de ahorro.
5. Pasar SQLite a Postgres si hay más de una ciudad.
