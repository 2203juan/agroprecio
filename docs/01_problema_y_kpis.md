# Problema, usuarios y KPIs

## Problema de negocio

Los restaurantes pequeños de Cali (corrientazo, comida casera, comidas rápidas) compran frutas, verduras y tubérculos cada semana, casi siempre en Cavasa o en galerías que se surten de ahí. Esos precios cambian mucho. En los datos del SIPSA, más de dos tercios de las semanas un producto sube o baja más de 3 %.

Sin información, el dueño compra cuando se le acaba el producto y paga lo que esté el día. No sabe si le convenía adelantar la compra o esperar.

La información existe: el DANE publica cada semana los precios de más de 90 mercados. Pero viene en un Excel de nueve hojas y miles de filas, pensado para analistas, no para quien está en la cocina.

## Usuario objetivo

**Persona principal:** dueña o dueño de un restaurante de 20 a 60 almuerzos diarios en Cali. Hace las compras él mismo o las encarga. Usa WhatsApp todo el día, no usa hojas de cálculo y no tiene tiempo para leer boletines.

**Lo que necesita:** saber el jueves o el viernes qué conviene comprar ya y qué puede esperar, en dos o tres líneas.

**Usuarios secundarios:** tenderos de barrio y casinos de empresas pequeñas, con la misma necesidad.

## Propuesta de valor

"Cada semana te decimos qué insumos van a subir en Cavasa para que los compres antes."

## Impacto esperado

Si un restaurante gasta $3.000.000 al mes en insumos frescos y AgroPrecio le ayuda a ahorrar 1 %, son $30.000 al mes. Es poco para un solo restaurante, pero el producto cuesta casi cero de operar porque los datos son públicos y el modelo es liviano. El valor está en el volumen de usuarios y en sumar después otros servicios, como compras agrupadas o domicilios desde Cavasa.

## Alineación estratégica

- Usa datos abiertos del Estado (SIPSA - DANE), lo que reduce el costo de adquirir datos.
- Va en la línea de la Política de Explotación de Datos del país (CONPES 3920): convertir datos públicos en decisiones.
- Es un MVP replicable: cambiar el mercado (`market` en `config/config.yaml`) lleva el producto a otra ciudad sin tocar código.

## Vigencia de los datos

El DANE publica los viernes, pero a veces con rezago: el 22 de noviembre de 2026 el último boletín disponible era el del 31 de octubre al 6 de noviembre. Cuando la semana recomendada ya pasó, el dashboard lo avisa y Prometheus dispara una alerta.

## OKR del MVP

**Objetivo:** demostrar que los datos del SIPSA sirven para dar una recomendación de compra útil y confiable.

| Resultado clave | Meta | Estado en la Beta |
|---|---|---|
| KR1: el modelo le gana al baseline de persistencia en F1 macro | > baseline | 0,47 contra 0,40 ✅ |
| KR2: ahorro simulado en el periodo de prueba | ≥ 1 % | 1,0 %, en el límite: el intervalo va de 0,4 % a 1,7 % ⚠️ |
| KR3: el pipeline corre solo cada semana, sin intervención | 4 semanas seguidas | Programado en GitHub Actions y Airflow, falta acumular corridas |
| KR4: reglas de calidad de datos que pasan | 100 % | 11 de 11 ✅ |
| KR5: restaurantes que prueban el boletín y dicen que lo usarían | 5 | 0 de 5. Plan en [07_validacion.md](07_validacion.md); la respuesta se guarda desde el dashboard |

## KPIs

| KPI | Tipo | Cómo se mide | Dónde |
|---|---|---|---|
| F1 macro y accuracy contra baseline | Modelo | Corte temporal, últimas 20 semanas | `models/registry.json` |
| Acierto de las últimas 8 semanas (incluye backtest) | Modelo | Predicción contra resultado real | Tabla `monitoreo` |
| Acierto real: solo predicciones hechas antes del resultado | Modelo | Igual, sin el backtest. Todavía no hay ninguna con resultado | Tabla `monitoreo`, columna `accuracy_real` |
| Restaurantes a los que les sirvió | Negocio | Respuesta a "¿te sirvió?" | Tabla `opiniones`, Grafana |
| Días desde el último boletín | Datos | Fecha de hoy menos el fin del boletín | `GET /vigencia`, Grafana |
| Ahorro simulado | Negocio | Compra anticipada cuando el modelo dice "sube" frente a comprar la semana siguiente | `registry.json` |
| Reglas de calidad que pasan | Datos | 12 reglas por corrida | Tabla `calidad_datos` |
| Productos con drift | Datos | z-score del cambio semanal > 3 | Tabla `drift` |
| Boletines del LLM descartados por cifras inventadas | LLM | Validación de números contra los datos | `logs/llm.jsonl` |
| Tiempo de corrida del pipeline | Operación | Log | `logs/pipeline.log` (~25 s sin descarga) |
