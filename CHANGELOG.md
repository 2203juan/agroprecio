# Historial de versiones

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
