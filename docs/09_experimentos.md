# Experimentos del modelo

Dos rondas: la v0.7 (datos nuevos y red neuronal) y, más abajo, la v0.6.

## v0.7: el diario del SIPSA

### El problema

La v0.6 daba F1 0,472 y accuracy 0,478 en la prueba. Antes de cambiar nada se probó solo el algoritmo, con los mismos datos: una red neuronal, ensambles más grandes y más semillas. Todo quedó entre 0,49 y 0,50 de F1 en validación. El límite no era el modelo sino los datos: la variable más útil tenía una correlación de 0,12 con lo que pasa la semana siguiente.

### El dato nuevo

El DANE publica, además del boletín semanal, el precio de **cada día de mercado** en las centrales principales, y un servicio web lo entrega completo desde febrero de 2020. Cavasa tiene mercado lunes y jueves; Corabastos, todos los días.

- En 16 de los 20 productos, el precio semanal del boletín es exactamente el promedio de los días de Cavasa (razón 1,000 y correlación 1,000 en 177 semanas). Es la misma medición, vista por dentro.
- El promedio de la semana esconde hacia dónde iba el precio. Si Cavasa cerró el jueves por encima de su promedio, o Corabastos subió de lunes a viernes, la semana siguiente suele arrancar desde ahí.
- Cilantro, yuca, papa parda y zanahoria no tienen un diario equivalente en Cavasa. Usan solo las variables de Corabastos, la región y el país.

Nueve variables nuevas (`DAILY_FEATURES` en `src/transform/diario.py`). Su relación con el cambio siguiente es entre dos y tres veces la de las anteriores:

| Variable | Qué mide | Correlación |
|---|---|---|
| `pais_cierre_vs_media` | Cierre de la semana frente a su promedio, mediana de los mercados del país | 0,33 |
| `pais_amplitud_intra` | Proporción de mercados que subieron menos los que bajaron dentro de la semana | 0,33 |
| `cora_cierre_vs_media`, `cora_cambio_intra` | Lo mismo en Corabastos | 0,29 |
| `dia_cambio_intra` | Jueves frente a lunes en Cavasa | 0,28 |
| `dia_ultimo_vs_semana` | Último día de Cavasa frente al precio semanal | 0,27 |
| `cora_cambio_cierre` | Cierre de Corabastos frente al cierre anterior | 0,25 |
| `region_cierre_vs_media` | Cierre frente al promedio en Armenia, Pereira, Popayán y Cali | 0,22 |
| `dia_cambio_cierre` | Cierre de Cavasa frente al cierre anterior | 0,09 |

Solo usan días de la semana que ya terminó: hay un test que quita los días posteriores y comprueba que no cambian.

### Resultados en validación

Los mismos cinco bloques de 14 semanas, sin tocar la prueba (`make experiments`):

| Variante | F1 macro | Peor bloque | Accuracy | Ahorro simulado |
|---|---|---|---|---|
| HistGradientBoosting + ExtraTrees, sin el diario (v0.6) | 0,496 | 0,474 | 0,499 | 1,45 % |
| Regresión logística, con el diario | 0,549 | 0,493 | 0,553 | 1,98 % |
| ExtraTrees, con el diario | 0,540 | 0,508 | 0,544 | 1,83 % |
| HistGradientBoosting, con el diario | 0,534 | 0,507 | 0,540 | 1,95 % |
| HistGradientBoosting + ExtraTrees, con el diario | 0,546 | 0,524 | 0,551 | 1,92 % |
| **HistGradientBoosting + ExtraTrees + red neuronal, con el diario (v0.7)** | **0,546** | **0,509** | **0,553** | **2,10 %** |

- **La mejora viene de los datos.** Con el diario, hasta una regresión logística le gana al mejor modelo sin él.
- **La red neuronal aporta poco.** Sola iguala a los árboles. En el ensamble no sube el F1; sube algo el ahorro (de 1,92 % a 2,10 %) y el AUC. Es una red pequeña (32 neuronas, muy regularizada) y se promedian cinco semillas, porque una sola cambia mucho de una corrida a otra. Entra con un tercio del voto.

### Qué no ayudó

| Idea | Resultado |
|---|---|
| Reconstruir la serie semanal desde 2020 con el diario (el doble de historia) | F1 0,536 frente a 0,546: un poco peor. Antes de 2023 hay menos mercados y las variables de contexto no son comparables |
| Once variables más del diario (variación del último día, volatilidad dentro de la semana, la otra central de Cali, promedio del grupo) | Entre 0,547 y 0,564, dentro del ruido entre corridas |
| Redes más grandes (64-32, 128-64-32) | Igual o peor que la de 32 |
| Sumar la regresión logística al ensamble | Igual |
| Cambiar la regla de compra por la diferencia entre la probabilidad de subir y la de bajar | Ahorro de 2,10 % a 2,39 % en validación; no justifica cambiar lo que ve el usuario |
| Bajar un Excel por día del sitio del DANE | El servidor limita las descargas (error 429) después de unos 100 archivos. El servicio web entrega todo en una petición |

### Resultado en las 20 semanas de prueba

| | v0.6 | v0.7 | Intervalo de 95 % de la diferencia |
|---|---|---|---|
| Accuracy | 0,478 | 0,540 | +0,032 a +0,095 |
| F1 macro | 0,472 | 0,533 | +0,029 a +0,095 |
| Kappa de Cohen | 0,209 | 0,300 | |
| ROC AUC | 0,678 | 0,729 | |
| Log loss | 1,006 | 0,951 | |
| Ahorro simulado | 1,01 % | 1,13 % | -0,6 a +0,6 puntos |

Con el mercado de ejemplo del dashboard (50 almuerzos diarios), el ahorro real de esas 20 semanas pasa de $165.379 a $248.628 y sale mejor en 15 semanas en vez de 14.

### Cómo leerlo

- **La clasificación mejora de forma segura.** Es la primera vez que el intervalo de la diferencia de F1 no incluye el cero.
- **El ahorro simulado no mejora en la prueba.** En validación sí (de 1,45 % a 2,10 %), pero en estas 20 semanas la diferencia no se distingue de cero. El modelo acierta más la dirección, y eso todavía no se traduce en más plata con la regla de comprar antes lo que sube.
- **Sigue fallando casi la mitad de las veces.** Un acierto de 54 % en tres clases es mejor que el 40 % de repetir la semana anterior, pero no es un modelo para seguir a ciegas.
- **La prueba ya se había mirado** con la v0.6. Esta vez la decisión se tomó con la validación y la prueba se corrió una sola vez con el código final, pero son las mismas 20 semanas. La confirmación de verdad son las semanas nuevas.
- **Dependencia nueva:** si el servicio web del DANE falla, el pipeline sigue con el último diario descargado y la regla de calidad `diario_en_la_ultima_semana` lo avisa.

---

# Ronda anterior (v0.6)

## Punto de partida

La v0.5 era un Random Forest con 8 variables, entrenado solo con Cavasa. En las 20 semanas de prueba daba F1 macro 0,447 frente a 0,404 de repetir la semana anterior. La diferencia no era segura: con remuestreo por semanas, el intervalo de 95 % iba de -0,014 a +0,105.

Un modelo que acertara siempre cuándo sube el precio ahorraría 3,5 % en esas semanas. Ese es el techo del ahorro simulado.

## Cómo se comparó

- Cinco bloques de 14 semanas, del 28 de diciembre de 2024 al 9 de mayo de 2026. Cada uno se predice con un modelo entrenado solo con semanas anteriores.
- Las 20 semanas de prueba no se usaron para elegir.
- Todas las variantes se miden sobre las mismas filas de Cavasa.

```bash
make experiments    # ~1 minuto; guarda docs/experimentos.csv y, si hay servidor, en MLflow
```

## Resultados en validación

| Variante | F1 macro | Peor bloque | Ahorro simulado |
|---|---|---|---|
| Repetir la semana pasada | 0,408 | 0,359 | 0,16 % |
| Comprar todo hoy | 0,178 | 0,152 | 0,44 % |
| Random Forest, variables básicas (v0.5) | 0,422 | 0,399 | 0,75 % |
| Random Forest, todas las variables | 0,460 | 0,432 | 1,12 % |
| Regresión logística, todas las variables | 0,473 | 0,434 | 1,22 % |
| ExtraTrees, todas las variables | 0,482 | 0,440 | 1,19 % |
| ExtraTrees, todas, mercados de Cali | 0,483 | 0,438 | 1,37 % |
| HistGradientBoosting, todas, mercados de Cali | 0,491 | 0,462 | 1,36 % |
| **HistGradientBoosting + ExtraTrees, todas, mercados de Cali** | **0,496** | **0,474** | **1,45 %** |

La tabla completa está en [experimentos.csv](experimentos.csv).

## Qué ayudó

1. **Variables nuevas** (de 7 a 33 numéricas). Las que más se relacionan con el cambio siguiente son el cambio en Corabastos, qué tan lejos está Cavasa de su diferencia habitual con el país y qué pasó esa misma semana el año anterior. Ninguna es fuerte: la correlación más alta es 0,12.
2. **Entrenar con dos mercados de Cali** (Cavasa y Santa Elena): de 2.957 a 5.791 filas. Se evalúa solo en Cavasa.
3. **Promediar dos modelos distintos**: mejora sobre todo el peor bloque.
4. **Reajustar con todos los datos después de evaluar**. Antes el modelo en producción ignoraba las últimas 20 semanas; en validación eso costaba cerca de 0,012 de F1.

## Qué no ayudó

| Idea | Resultado |
|---|---|
| Entrenar con todos los mercados del país (casi 100 mil filas) | Peor que solo Cali |
| Dar más peso a Cavasa | Peor |
| Ajustar profundidad, hojas, regularización o tasa de aprendizaje | Entre 0,477 y 0,494, sin superar el ensamble |
| Sumar la regresión logística al ensamble | Igual F1, algo más de ahorro; no justifica la complejidad |
| Reentrenar cada semana en vez de cada 14 | Igual |
| Usar solo los últimos dos años | Peor |
| Cambiar la regla de compra (cambio esperado, umbrales) | Ninguna supera con claridad a la actual |
| Abastecimiento (hoja 1.10 del boletín) | No se probó: los boletines antiguos no la traen. El servicio web del SIPSA lo tiene por mes |

## Resultado en las 20 semanas de prueba

| | v0.5 | v0.6 | Intervalo de 95 % de la diferencia |
|---|---|---|---|
| F1 macro | 0,447 | 0,472 | -0,028 a +0,078 |
| Accuracy | 0,450 | 0,478 | |
| ROC AUC | 0,644 | 0,678 | |
| Ahorro simulado | 0,39 % | 1,01 % | +0,16 % a +1,06 % |

Con 12 semillas y órdenes distintos de las variables, el F1 es 0,469 ± 0,002 y el ahorro 0,99 % ± 0,05 %. La v0.6 publicada (semilla 42) está dentro de ese rango.

## Cómo leerlo

- **El ahorro mejora.** El intervalo de la diferencia no incluye el cero.
- **El F1 mejora poco.** Con 20 semanas no se puede asegurar que no sea azar, aunque en validación la mejora se repite en los cinco bloques.
- **La prueba dio menos que la validación** (0,472 frente a 0,496). Es lo esperable después de comparar muchas variantes.
- **La meta de 1 % queda en el límite.** El intervalo del ahorro va de 0,4 % a 1,7 %, y 3 de las 12 semillas quedan por debajo.
- **La prueba se miró dos veces:** una con el código de exploración (F1 0,461 y ahorro 0,86 %) y otra con el del proyecto, que calcula igual pero ordena distinto las variables. Para la siguiente mejora hará falta esperar semanas nuevas.
