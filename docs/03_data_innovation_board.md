# Data Innovation Board

Se puede cargar en el [Data Innovation Board](https://juankidd.github.io/databoard/) con **Importar JSON** usando [lienzos/databoard.json](lienzos/databoard.json).

## 01 · Explorar: comprender personas y datos

**Usuarios y contexto.** Dueños de restaurantes pequeños de Cali que compran insumos frescos cada semana en Cavasa o en galerías. Compran temprano, con poco tiempo, y deciden por costumbre o por lo que les dice el vendedor.

**Necesidades y retos.** Decidir cuándo comprar: adelantar la compra de lo que va a subir y esperar con lo que va a bajar. El reto es que la información de precios existe pero no llega en un formato que puedan usar.

**Datos existentes.**
- Boletín semanal de precios mayoristas del SIPSA (DANE): 92 mercados, 363 productos, precio mínimo, máximo y medio por kilo, y tendencia. Es público, sale los viernes (a veces con rezago) y viene en Excel.
- 182 boletines descargados (mayo de 2023 a octubre de 2026), unas 786 mil filas en silver.
- Calidad: buena en general. Hay 3 semanas faltantes, filas duplicadas dentro de algunos boletines, semanas cortas por festivos y el título de la semana viene en texto libre con formatos distintos.
- Lo controla el DANE; nosotros solo leemos.

**Hallazgos e hipótesis.**
- En Cavasa, cerca del 35 % de las semanas un producto sube más de 3 % y otro 35 % baja más de 3 %. La volatilidad es real.
- H1: el precio de Cavasa reacciona tarde frente a la mediana nacional, así que esa diferencia anticipa el cambio. *(Se validó en parte: está entre las variables con más relación, pero la relación es débil.)*
- H2: repetir la tendencia de la semana pasada es un baseline difícil de superar. *(El modelo lo supera en promedio; con 20 semanas de prueba la diferencia no es segura.)*
- H3: un mensaje corto en lenguaje natural es más útil que una tabla. *(Pendiente de validar con usuarios.)*

## 02 · Idear: diseñar una solución viable

**Idea basada en datos.** Un servicio que cada semana predice si 20 insumos clave van a subir, bajar o seguir estables en Cavasa, y lo traduce a una recomendación de compra que redacta un modelo de lenguaje.

**Datos adicionales.**
- Abastecimiento semanal por grupo de alimentos (hoja 1.10). Solo viene en los boletines recientes, así que todavía no alcanza para entrenar.
- Clima (IDEAM) en las zonas productoras, porque las lluvias mueven precios.
- Calendario de festivos y temporadas.
- Retroalimentación de los usuarios ("¿te sirvió?"), ya disponible en el dashboard.
- Todo sale de fuentes públicas o lo entrega el usuario de forma voluntaria.

**Prototipo y tecnología.**
- MVP: pipeline medallón en Python (Excel → Parquet → SQLite) con un baseline de persistencia.
- Alpha: Random Forest con registro de versiones, API en FastAPI y dashboard en React.
- Beta: boletín con un modelo de lenguaje, monitoreo de acierto y drift, CI/CD con GitHub Actions y todo en Docker.
- v0.5: MLflow, Prometheus, Grafana y Airflow; opinión del usuario y aviso de vigencia.
- v0.6: modelo nuevo elegido con validación en el tiempo.
- v0.7: se suman los precios diarios del SIPSA. El acierto pasa de 48 % a 54 %.

**Riesgos y ética.**
- El DANE publica con rezago y la recomendación llega vencida → aviso en el dashboard y alerta.
- El DANE cambia el formato del Excel → reglas de calidad que detienen el pipeline.
- El modelo se equivoca y el restaurante pierde plata → mostrar siempre la confianza y decir que es una estimación.
- El LLM inventa precios → validación automática de cifras y plantilla de respaldo.
- Sesgo: el modelo se entrenó con un periodo de inflación particular y puede fallar en otro contexto → monitoreo y reentrenamiento.
- Privacidad: los precios son públicos y no se procesan datos personales. Si se suma WhatsApp, se guardaría solo el número con consentimiento (Ley 1581 de 2012). La opinión guarda el nombre del restaurante y pide no escribir datos personales.
- Gobernanza: cada archivo de bronze tiene su URL y fecha de descarga en `manifest.csv`, y cada modelo queda versionado con los datos que usó.

## 03 · Evaluar: medir, aprender e iterar

**Puntos de contacto.** Dashboard web, boletín de texto (después, por WhatsApp) y la API para integrarse con sistemas de inventario o POS.

**Canales y adopción.** Piloto con 5 a 10 restaurantes conocidos de Cali, asociaciones de restaurantes y proveedores de Cavasa que reenvíen el boletín.

**KPIs y experimentos.**
- F1 del modelo contra el baseline (0,47 contra 0,40).
- Ahorro simulado en las 20 semanas de prueba (1,0 %, la meta es 1 %).
- Acierto de las últimas 8 semanas (backtest más predicciones reales), con reentrenamiento si baja de 0,40. Hoy está en 0,44.
- Experimento: durante 4 semanas, la mitad del piloto recibe el boletín y la otra mitad no; se compara cuánto pagaron por los mismos productos.

**Aprendizajes e iteración.**
- Se pudo leer bien un Excel "difícil": títulos con fechas en texto libre, semanas cortas y años que cambian dentro de la misma semana.
- El baseline de persistencia es fuerte. Lo que más ayudó fueron más datos (otro mercado de Cali y variables del país), no afinar parámetros ([experimentos](09_experimentos.md)).
- Se probaron otras reglas de compra y ninguna supera con claridad a comprar antes cuando dice "sube".
- El dashboard mostraba un ahorro que suponía acertar siempre; ahora lo dice.
- Se confundía el backtest con el acierto en producción; ahora se miden por separado.
- Faltó validar con usuarios reales ([plan](07_validacion.md)); es lo primero para la siguiente iteración.
