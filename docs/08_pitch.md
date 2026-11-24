# Guion del pitch

**Para quién:** dueños y administradores de restaurantes. No son técnicos: les importa cuánto ahorran y qué tan fácil es, no cómo está hecho.

Duración: 5 minutos más el cierre. Tres minutos con el [fondo animado](../pitch/README.md) y dos de demostración en vivo.

## Guion

El fondo no trae texto para leer: muestra las cifras y tú las cuentas. Cada escena entra completa en un par de segundos y con `→` pasas a la siguiente; con `←` vuelves. La barra de abajo se llena en el tiempo previsto.

| Tiempo | Escena | Qué decir |
|---|---|---|
| 0:00 | Portada | Saludo y nombre. |
| 0:06 | Comprar a ciegas | Usted compra verdura cada semana sin saber si mañana sube. Siete de cada diez semanas, un producto de Cavasa cambia más de 3 %. |
| 0:35 | 4.000 filas de Excel | Esos precios son públicos y gratis: el DANE los publica cada viernes, en un Excel de más de 4.000 filas. Nadie en una cocina lo abre. |
| 1:05 | ¿Qué compro ya y qué espero? | AgroPrecio lo lee por usted y le responde una sola pregunta. Esta semana: 3 productos para comprar ya y 3 para esperar. En los otros 14 no hay una señal clara, y AgroPrecio lo dice: se compran como siempre. |
| 1:35 | Fácil, cada semana | Anota su lista de mercado, ve qué comprar y qué esperar, sabe cuánto le cuesta la semana y lo comparte por WhatsApp con quien compra. No instala nada, no cambia de proveedor y la decisión es suya. |
| 2:05 | ¿Cuánto me ahorro? | Tomemos una cevichería grande, de 500 platos diarios de lunes a sábado: compra unos 5,3 millones de pesos de mercado a la semana, sobre todo limón y cebolla, que cambian mucho de precio. En las últimas 20 semanas, con los precios que publicó el DANE, siguiendo la recomendación habría pagado 3,2 millones de pesos menos: 3 % del mercado. Son cerca de 8,5 millones al año. Si usted vende 50 platos, divida por diez: unos 325.000 pesos en esas 20 semanas. Le salió mejor en 14 de las 20 semanas; en 5 esperar salió más caro y en una dio igual, y por eso en cada producto le dice cuántas veces ha acertado. |
| 2:35 | ¿Lo probamos? | Buscamos 5 restaurantes. Son 15 minutos para empezar, es gratis y no hay que instalar nada. Veámoslo en vivo. |
| 3:00 | **Demostración** (abajo) | Solo el dashboard. |
| 5:00 | Cierre | Los precios ya son públicos; falta que lleguen a su cocina. |

**Cuidado con la cifra del ahorro.** Los $3.258.885 son reales en el sentido de que usan las recomendaciones de cada semana y los precios que salieron después, pero ningún restaurante compró así: es un mercado de ejemplo, no un cliente. Es 3 % del mercado, el mismo porcentaje para un negocio pequeño: la cifra se ve grande porque el ejemplo vende 500 platos, unas diez veces más que los restaurantes de 20 a 60 a los que apunta el producto. Además es el caso favorable: la cevichería gasta casi todo en limón y cebolla, donde más se nota la recomendación. Con el mercado de un restaurante de almuerzos del mismo tamaño el ahorro es 1,8 % ($2.546.565 en las mismas 20 semanas); si alguien pregunta, dilo. La cuenta supone que lo que iba a bajar se pudo dejar para la semana siguiente y no descuenta lo que se dañe o haga falta mientras tanto. Los $8.500.000 al año son esas 20 semanas llevadas a 52, no una promesa. La misma sección está en el dashboard, por si alguien pide verla.

## Demostración (2 minutos)

Antes de empezar: `make docker` y `make status`. Deja abiertas dos pestañas: el fondo animado y el dashboard. Al terminar, vuelve a la pestaña del fondo y pasa a la escena de cierre con `→`.

1. **De un vistazo.** Lee en voz alta las tres listas: qué comprar ya, qué esperar y qué sigue igual.
2. **Mi lista.** Carga el mercado de ejemplo de la cevichería (500 ceviches diarios), cambia los kilos de un producto y muestra cómo se actualiza el costo de la semana. Baja a *Lo que habrías ahorrado con esta lista*: es la misma cifra del fondo, semana por semana.
3. Señala un producto de *Compra ya*: el precio esperado y cuántas veces ha acertado.
4. **WhatsApp.** Muestra el botón que envía la lista a quien hace la compra.
5. Si aparece **Recomendación vencida**, dilo: el producto avisa cuando el DANE va atrasado.

MLflow y Grafana no hacen parte de esta demostración. Ábrelos solo si alguien pregunta cómo funciona por dentro.

Plan B si falla internet: todo corre en el portátil, menos *Buscar boletín nuevo*. Las capturas están en el README.

## Preguntas probables

### De un restaurante

**¿Cuánto cuesta?** La versión básica es gratis. Los datos son públicos y no hay que instalar nada.

**¿Y si se equivoca?** Solo recomienda comprar ya o esperar cuando tiene una señal clara, y ahí acierta 6 de cada 10 veces. En el resto dice que no sabe. Cada producto muestra cuántas de las últimas 8 semanas acertó, y la decisión siempre es suya. En promedio, hacerle caso sale mejor que no hacerlo.

**¿Sirve para lo que se daña rápido?** En cilantro o lechuga, guardar una semana también cuesta. Ahí la recomendación es una señal, no una orden.

**¿Yo compro en otra plaza?** Hoy los precios son de Cavasa. Sirven de referencia para Cali, pero no son los de su proveedor.

**¿Qué tengo que hacer cada semana?** Abrir la página, mirar las tres listas y, si quiere, enviarlas por WhatsApp.

### Si alguien pregunta cómo funciona por dentro

**¿Por qué un modelo con 54 % de acierto?** Ese es el acierto opinando sobre todo; en lo que sí recomienda, que es más o menos la mitad de los casos, acierta 62 %. Son tres clases, y la regla de repetir la semana anterior acierta 40 %. Antes acertaba 48 %: la mejora vino de sumar los precios de cada día de mercado, que dicen cómo cerró la semana, no de cambiar el algoritmo.

**¿Usa redes neuronales?** Sí, una pequeña dentro de un ensamble con dos modelos de árboles. Aporta poco: con tan pocos datos, lo que más pesa es qué información entra.

**¿Cómo eligieron el modelo?** Con cinco bloques de validación anteriores a la prueba. Ver [experimentos](09_experimentos.md).

**¿La mejora es segura?** La del acierto sí: frente a la versión anterior sube entre 3 y 10 puntos. La del ahorro no: en la prueba queda igual, cerca de 1 %.

**¿El acierto en producción cuál es?** Todavía no hay: las 20 predicciones reales esperan el siguiente boletín. El 51 % de las últimas 8 semanas es del backtest.

**¿Por qué dice que la recomendación está vencida?** El DANE publica con rezago. El pipeline revisa dos veces por semana y el dashboard avisa.

**¿Ya lo usó alguien?** No. El plan de validación está escrito y la opinión del usuario ya queda guardada, pero falta hacerlo.

**¿Para qué sirve el modelo de lenguaje?** Para redactar el boletín en lenguaje sencillo. Si inventa un precio se descarta, y sin clave de API el producto funciona con la plantilla.

**¿Por qué Airflow, si ya hay GitHub Actions?** GitHub Actions corre sin servidor propio. Airflow sirve para desplegarlo en una máquina y ver, reintentar y auditar cada etapa.

**¿Cuánto cuesta operarlo?** Los datos son gratis y todo corre en un portátil. El único pago posible es la llamada al modelo de lenguaje, una por corrida.

## Antes de presentar

- [ ] Ensayar con cronómetro
- [ ] Generar un boletín con el modelo de lenguaje y revisarlo
- [ ] Hacer al menos dos pruebas con restaurantes y contar qué pasó
- [ ] Actualizar las cifras de este guion si llegó un boletín nuevo
