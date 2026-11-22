# Experimentos del modelo (v0.6)

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
| Abastecimiento (hoja 1.10 del boletín) | No se probó: los boletines antiguos no la traen |

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
