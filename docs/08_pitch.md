# Guion del pitch

Duración: 5 minutos, con 2 de demostración, más preguntas.

## Guion

| Tiempo | Qué decir | Qué mostrar |
|---|---|---|
| 0:00 | Un restaurante pequeño compra verdura cada semana sin saber si mañana sube. Siete de cada diez semanas, un producto de Cavasa cambia más de 3 %. | Portada |
| 0:30 | El DANE publica esos precios gratis, en un Excel de más de 4.000 filas. Nadie en una cocina lo abre. | El Excel del boletín |
| 1:00 | AgroPrecio lo lee por él y responde una pregunta: qué compro ya y qué espero. | Dashboard |
| 1:15 | **Demostración** (abajo). | Dashboard, MLflow y Grafana |
| 3:15 | El modelo le gana en promedio a la regla más simple: F1 0,47 frente a 0,40. El ahorro simulado pasó de 0,4 % a 1,0 %, justo en la meta. Se equivoca más de la mitad de las veces, así que cuidamos la operación: 11 reglas de calidad, registro de modelos y alertas. | Tabla del README |
| 4:00 | Lo que sigue: probarlo con 5 restaurantes y sumar clima y abastecimiento. | [Plan de validación](07_validacion.md) |
| 4:30 | Cierre: los datos ya son públicos; falta que lleguen a quien compra. | Portada |

## Demostración (2 minutos)

Antes de empezar: `make docker` y `make status`. Deja abiertas tres pestañas: dashboard, MLflow y Grafana.

1. **Dashboard.** Cambia los kilos de un producto y muestra cómo se actualiza el costo.
2. Señala una recomendación *Compra ya*, su rango esperado y cuántas veces acertó.
3. Si aparece **Recomendación vencida**, dilo: es una función, no un error. El producto avisa cuando el DANE va atrasado.
4. Responde **¿Te sirvió?** y abre Grafana: la respuesta aparece en unos segundos.
5. **MLflow.** Abre el modelo `champion` y compáralo con los baselines.

Plan B si falla internet: todo corre en el portátil, menos *Buscar boletín nuevo*. Las capturas están en el README.

## Preguntas probables

**¿Por qué un modelo con 48 % de acierto?** Son tres clases y la regla de repetir la semana anterior acierta 40 %. Los precios tienen poca señal: la variable más útil tiene una correlación de 0,12. Aun así, comprar antes cuando dice *sube* ahorra 1 %; acertar siempre ahorraría 3,5 %.

**¿Cómo eligieron el modelo?** Con cinco bloques de validación anteriores a la prueba. Lo que más ayudó fueron variables del país y otro mercado de Cali. Ver [experimentos](09_experimentos.md).

**¿La mejora es segura?** La del ahorro sí: la diferencia va de +0,2 a +1,1 puntos. La del F1 no se puede asegurar con 20 semanas.

**¿El acierto en producción cuál es?** Todavía no hay: las 20 predicciones reales esperan el siguiente boletín. El 44 % de las últimas 8 semanas es del backtest.

**¿Por qué dice que la recomendación está vencida?** El DANE publica con rezago. El pipeline revisa dos veces por semana y el dashboard avisa.

**¿Ya lo usó alguien?** No. El plan de validación está escrito y la opinión del usuario ya queda guardada, pero falta hacerlo.

**¿Para qué sirve Claude?** Para redactar el boletín en lenguaje sencillo. Si inventa un precio se descarta, y sin clave de API el producto funciona con la plantilla.

**¿Por qué Airflow, si ya hay GitHub Actions?** GitHub Actions corre sin servidor propio. Airflow sirve para desplegarlo en una máquina y ver, reintentar y auditar cada etapa.

**¿Cuánto cuesta operarlo?** Los datos son gratis y todo corre en un portátil. El único pago posible es la llamada a Claude, una por corrida.

## Antes de presentar

- [ ] Ensayar con cronómetro
- [ ] Generar un boletín con Claude y revisarlo
- [ ] Hacer al menos dos pruebas con restaurantes y contar qué pasó
- [ ] Actualizar las cifras de este guion si llegó un boletín nuevo
