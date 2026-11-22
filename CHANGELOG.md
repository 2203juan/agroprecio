# Historial de versiones

## v0.6.0 · Modelo
- Modelo nuevo: promedio de HistGradientBoosting y ExtraTrees, con 33 variables y dos mercados de Cali. F1 de 0,447 a 0,472 y ahorro simulado de 0,39 % a 1,01 % en la prueba.
- El modelo en producción se reajusta con todos los datos después de evaluarse.
- `make experiments`: compara variantes con validación hacia adelante.
- Baseline nuevo: comprar todo hoy.
- El dashboard aclara que el ahorro de la lista supone que las predicciones se cumplen.
- Las versiones anteriores se siguen pudiendo evaluar.
- Dashboard rediseñado para celular: resumen arriba, una tarjeta por producto con la recomendación visible, detalle en un panel, pizarra con filtro y deshacer al quitar.
- Colores de semáforo para la recomendación: verde para *Compra ya* y ámbar para *Espera*. El rojo queda para errores y el cambio de la semana pasada va en gris. *Normal* ahora es *Como siempre*.
- Botones para enviar la lista y el boletín por WhatsApp, boletín en tres listas y buscador para agregar productos.
- El precio se muestra con su fecha en vez de "hoy".
- nginx ya no deja en caché la página, para que no quede la versión vieja tras un despliegue.

## v0.5.0 · Operación
- MLflow: experimentos, registro de modelos con alias `champion` y trazas del boletín. Es opcional: sin servidor, el pipeline sigue igual.
- Prometheus (`/prometheus`, cinco alertas) y dashboard de Grafana precargado.
- Airflow: DAG `agroprecio_semanal` con una tarea por etapa.
- Pipeline por etapas: `python main.py --etapa silver`.
- Pregunta "¿te sirvió?" en el dashboard y tabla `opiniones`.
- Aviso de recomendación vencida y endpoint `/vigencia`.
- El monitoreo separa el acierto real del backtest.
- Corregido: un reentrenamiento reemplazaba las predicciones reales por las del backtest.
- Corregido: la API programaba la actualización en hora UTC, no en la de Colombia.
- Silver usa 30 % menos memoria con el mismo resultado.
- El pipeline de GitHub Actions corre también los miércoles.
- Tests de la API, el boletín, el monitoreo, el pipeline y MLflow (60 en total).
- AI Canvas, plan de validación y guion del pitch.
- Endpoint `/metrics` con la tabla de métricas de cada versión del modelo frente a los baselines, métricas por clase, matriz de confusión y métricas en producción.
- El registro guarda las métricas completas de cada entrenamiento nuevo.
- Fotos de plazas de mercado en el dashboard: portada, tarjeta del mercado y banda final, con banderines y colores tomados de las fotos.

## v0.4.0 · Beta para el restaurante
- Lista de mercado del restaurante guardada en la base, con costo hoy, costo esperado la próxima semana y costo siguiendo la recomendación.
- Rango de precio esperado para la próxima semana por producto.
- Aciertos del modelo por producto en las últimas 8 semanas.
- Botón para buscar el boletín nuevo del DANE y actualización automática los sábados desde la API.
- Dashboard rediseñado con estilo de plaza de mercado: toldo, letrero, pizarra de precios y detalle por producto.

## v0.3.0 · Beta
- Boletín semanal redactado con Claude, con validación de cifras y plantilla de respaldo.
- Registro de cada llamada al LLM en `logs/llm.jsonl`.
- Monitoreo: acierto semanal, drift por producto y bandera de reentrenamiento.
- Reentrenamiento automático solo cuando el monitoreo lo pide y hay semanas nuevas.
- Docker Compose con pipeline, API y dashboard.
- CI en GitHub Actions y pipeline programado los sábados.

## v0.2.0 · Alpha
- Random Forest con corte temporal, comparado contra dos baselines.
- Registro de modelos (`models/registry.json`) con regla de promoción a producción.
- Ahorro simulado como métrica de negocio.
- Reglas de calidad de datos para silver y gold, guardadas por corrida.
- API en FastAPI y dashboard en React.

## v0.1.0 · MVP
- Descarga incremental de los boletines semanales del SIPSA con manifest.
- Lectura de los Excel y limpieza a una tabla silver de todo el país.
- Serie semanal de Cavasa para 20 productos en gold.
- Carga a SQLite y baseline de persistencia.
