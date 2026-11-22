# Guion del pitch

**Para quién:** dueños y administradores de restaurantes. No son técnicos: les importa cuánto ahorran y qué tan fácil es, no cómo está hecho.

Duración: 5 minutos más el cierre. Tres minutos con el [fondo animado](../pitch/README.md) y dos de demostración en vivo.

## Guion

El fondo no trae texto para leer: muestra las cifras y tú las cuentas. Cada escena se queda en pantalla hasta que pasas a la siguiente con `→`, y la barra de abajo se llena en el tiempo previsto.

| Tiempo | Escena | Qué decir |
|---|---|---|
| 0:00 | Portada | Saludo y nombre. |
| 0:06 | Comprar a ciegas | Usted compra verdura cada semana sin saber si mañana sube. Siete de cada diez semanas, un producto de Cavasa cambia más de 3 %. |
| 0:35 | 4.000 filas de Excel | Esos precios son públicos y gratis: el DANE los publica cada viernes, en un Excel de más de 4.000 filas. Nadie en una cocina lo abre. |
| 1:05 | ¿Qué compro ya y qué espero? | AgroPrecio lo lee por usted y le responde una sola pregunta. Esta semana: 9 productos para comprar ya, 8 para esperar y 3 como siempre. |
| 1:35 | Fácil, cada semana | Anota su lista de mercado, ve qué comprar y qué esperar, sabe cuánto le cuesta la semana y lo comparte por WhatsApp con quien compra. No instala nada, no cambia de proveedor y la decisión es suya. |
| 2:05 | ¿Cuánto me ahorro? | Cerca de 1 % del mercado. Si compra un millón a la semana, son unos 10.000 pesos semanales y cerca de 520.000 al año. Lo probamos con 20 semanas de precios reales. No siempre acierta, y por eso en cada producto le dice cuántas veces ha acertado. |
| 2:35 | ¿Lo probamos? | Buscamos 5 restaurantes. Son 15 minutos para empezar, es gratis y no hay que instalar nada. Veámoslo en vivo. |
| 3:00 | **Demostración** (abajo) | Solo el dashboard. |
| 5:00 | Cierre | Los precios ya son públicos; falta que lleguen a su cocina. |

**Cuidado con la cifra del ahorro.** El 1 % sale de una simulación con precios pasados, no de restaurantes reales, y puede estar entre 0,4 % y 1,7 % (entre 208.000 y 884.000 pesos al año con el mismo ejemplo). Tampoco descuenta lo que se dañe por guardar un producto una semana. Por eso el fondo dice "podrías ahorrar" y "cerca de": no lo presentes como un ahorro garantizado.

## Demostración (2 minutos)

Antes de empezar: `make docker` y `make status`. Deja abiertas dos pestañas: el fondo animado y el dashboard. Al terminar, vuelve a la pestaña del fondo y pasa a la escena de cierre con `→`.

1. **De un vistazo.** Lee en voz alta las tres listas: qué comprar ya, qué esperar y qué sigue igual.
2. **Mi lista.** Cambia los kilos de un producto y muestra cómo se actualiza el costo de la semana.
3. Señala un producto de *Compra ya*: el precio esperado y cuántas veces ha acertado.
4. **WhatsApp.** Muestra el botón que envía la lista a quien hace la compra.
5. Si aparece **Recomendación vencida**, dilo: el producto avisa cuando el DANE va atrasado.

MLflow y Grafana no hacen parte de esta demostración. Ábrelos solo si alguien pregunta cómo funciona por dentro.

Plan B si falla internet: todo corre en el portátil, menos *Buscar boletín nuevo*. Las capturas están en el README.

## Preguntas probables

### De un restaurante

**¿Cuánto cuesta?** La versión básica es gratis. Los datos son públicos y no hay que instalar nada.

**¿Y si se equivoca?** Se equivoca más o menos una de cada dos veces. Por eso cada producto muestra cuántas de las últimas 8 semanas acertó, y la decisión siempre es suya. En promedio, hacerle caso sale mejor que no hacerlo.

**¿Sirve para lo que se daña rápido?** En cilantro o lechuga, guardar una semana también cuesta. Ahí la recomendación es una señal, no una orden.

**¿Yo compro en otra plaza?** Hoy los precios son de Cavasa. Sirven de referencia para Cali, pero no son los de su proveedor.

**¿Qué tengo que hacer cada semana?** Abrir la página, mirar las tres listas y, si quiere, enviarlas por WhatsApp.

### Si alguien pregunta cómo funciona por dentro

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
