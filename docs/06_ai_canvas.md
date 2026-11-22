# AI Canvas

El [Business Model Canvas](02_canvas.md) describe el negocio. Este lienzo describe la decisión que apoya el modelo, con los datos y la retroalimentación que necesita.

| Bloque | AgroPrecio |
|---|---|
| **Predicción** | Si el precio de cada uno de 20 insumos en Cavasa sube más de 3 %, baja más de 3 % o queda estable la semana siguiente |
| **Juicio** | Comprar antes algo que no subió cuesta poco si el producto aguanta; no comprar a tiempo algo que subió cuesta la diferencia de precio. En perecederos como cilantro y lechuga, guardar una semana también tiene costo: por eso la decisión final es del restaurante |
| **Acción** | `sube` → comprar esta semana · `baja` → esperar · `estable` → comprar como siempre |
| **Resultado** | Cuánto costó la lista de mercado siguiendo la recomendación frente a comprar todo hoy o esperar todo |
| **Datos de entrenamiento** | Boletines semanales del SIPSA desde mayo de 2023, unas 6.500 semanas-producto con resultado conocido en Cavasa y Santa Elena |
| **Datos de entrada** | Historia del precio en Cavasa, precios del país, la región y Corabastos, y época del año |
| **Retroalimentación** | El precio real de la semana siguiente, que llega en el próximo boletín, y la respuesta del restaurante a "¿te sirvió?" |
| **Impacto en la operación** | El dueño consulta el dashboard antes de comprar; no cambia de proveedor ni de sistema |

## Viabilidad

| Dimensión | Pregunta | Respuesta hoy |
|---|---|---|
| Técnica | ¿Se puede predecir mejor que la regla más simple? | En promedio sí: F1 macro 0,47 frente a 0,40 de repetir la semana anterior. Con 20 semanas de prueba la diferencia no es segura |
| Datos | ¿Llegan a tiempo los datos? | No siempre. El DANE publica los viernes, pero el 22 de noviembre de 2026 el último boletín disponible era el del 31 de octubre al 6 de noviembre. El dashboard avisa cuando la recomendación ya venció |
| Negocio | ¿El ahorro justifica usarlo? | Sin demostrar en la práctica. El ahorro simulado es 1,0 % (entre 0,4 % y 1,7 %) y la meta es 1 %. Falta medirlo con restaurantes ([plan](07_validacion.md)) |

## Riesgos de la decisión automática

| Riesgo | Control |
|---|---|
| El modelo se equivoca más de la mitad de las veces | Cada producto muestra cuántas de sus últimas 8 semanas acertó y el rango esperado |
| La recomendación está vencida | Aviso en el dashboard y alerta `RecomendacionVencida` en Prometheus |
| Claude escribe un precio que no existe | `numbers_are_grounded` descarta el texto y se usa la plantilla |
| El modelo se degrada | Acierto de las últimas 8 semanas, drift y regla de reentrenamiento |
