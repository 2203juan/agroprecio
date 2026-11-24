# Historial de versiones

## Sin publicar
- Respaldo del diario: el servicio web del SIPSA no responde desde GitHub Actions. El pipeline parte de una copia en el repositorio y se pone al día con los anexos diarios en Excel.
- Ahorro real de la lista de mercado: compara, con los precios que ya pasaron, comprar todo ya frente a seguir la recomendación, semana por semana.
- Mercado de ejemplo para un restaurante de 500 almuerzos diarios de lunes a sábado (antes 50), y un segundo ejemplo de cevichería.
- El ahorro real muestra aparte las compras que se aplazaron: cuánto menos se pagó en ellas, cuántas veces salió bien y la mejor semana.
- Despliegue en Azure App Service (plan gratuito): imagen única (`Dockerfile.nube`) con página, API, base y modelo. El workflow semanal la publica en ghcr.io.
- Modo público (`AGRO_PUBLICO=1`): la lista se guarda en el navegador, el botón de actualizar no aparece y las opiniones sobreviven a los reinicios.
- Fondo animado para el pitch (`pitch/`) y guion adaptado a dueños de restaurante.

## v0.7.1 · Señal clara
- El modelo solo recomienda *Compra ya* o *Espera* con confianza de 50 % o más; en el resto dice *Como siempre, sin señal clara*. En la prueba recomienda en 54 % de los casos y acierta 62 %.
- La lista de mercado, el ahorro real y el boletín usan la recomendación, no la predicción cruda.
- `/metrics` y el registro guardan `cobertura_senal_clara` y `accuracy_senal_clara`.

## v0.7.0 · Precios diarios
- Fuente nueva: precios de cada día de mercado, por el servicio web del SIPSA (desde 2020, una descarga al día).
- Nueve variables sobre cómo cerró la semana en Cavasa, Corabastos, la región y el país.
- El ensamble suma una red neuronal pequeña (promedio de cinco semillas).
- En la prueba: accuracy de 0,478 a 0,540, F1 de 0,472 a 0,533 y ROC AUC de 0,678 a 0,729. El ahorro simulado queda igual (1,13 %).
- El pipeline reentrena solo cuando el código trae otra receta de modelo.
- Regla de calidad nueva: avisa si la última semana no tiene precios diarios.

## v0.6.0 · Modelo
- Modelo nuevo: promedio de HistGradientBoosting y ExtraTrees, con 33 variables y dos mercados de Cali. F1 de 0,447 a 0,472 y ahorro simulado de 0,39 % a 1,01 % en la prueba.
- El modelo en producción se reajusta con todos los datos después de evaluarse.
- `make experiments`: compara variantes con validación hacia adelante.
- Baseline nuevo: comprar todo hoy.
- El dashboard aclara que el ahorro de la lista supone que las predicciones se cumplen.
- Las versiones anteriores se siguen pudiendo evaluar.
- Dashboard rediseñado para celular: resumen arriba, una tarjeta por producto con la recomendación visible, detalle en un panel, pizarra con filtro y deshacer al quitar.
- Colores de semáforo para la recomendación: verde para *Compra ya* y ámbar para *Espera*. El rojo queda para errores y el cambio de la semana pasada va en gris. *Normal* ahora es *Como siempre*.
- Estilo nuevo, de volante de frutas y verduras: fondo claro, verde y amarillo, tarjetas de producto y tipografía Bricolage Grotesque con DM Sans. Ya no hay tema oscuro.
- Fotos reales de los 20 productos, de Wikimedia Commons, con sus créditos y licencias en `frontend/public/img/productos/CREDITOS.md`.
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
- Boletín semanal redactado con un modelo de lenguaje, con validación de cifras y plantilla de respaldo.
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
