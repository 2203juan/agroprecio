# Model card: predictor semanal de precios en Cavasa

## Uso previsto
Dar una recomendación de compra semanal (comprar ya, esperar o comprar normal) a restaurantes pequeños de Cali. **No** sirve para fijar precios, negociar contratos ni para mercados distintos a Cavasa sin reentrenar.

## Datos
- Fuente: boletín semanal de precios mayoristas del SIPSA (DANE).
- Se evalúa en Cali, Cavasa, y se entrena con Cavasa y Santa Elena. Productos: los 20 de `config/config.yaml`.
- Periodo: de mayo de 2023 a octubre de 2026.
- Evaluación: se entrena hasta 20 semanas antes del final (5.791 filas) y se prueba con las últimas 20 semanas de Cavasa (400 filas).
- Producción: la misma receta, reajustada con todas las filas (6.531). Las métricas son siempre del modelo que no vio la prueba.

## Objetivo
Cambio del precio medio la semana siguiente:
- `sube` si es mayor a +3 %
- `baja` si es menor a -3 %
- `estable` si queda en medio

Distribución: 36 % baja, 36 % sube y 28 % estable.

## Variables
33 numéricas más el producto (one-hot). Ninguna mira al futuro; hay un test que lo comprueba.

| Grupo | Variables |
|---|---|
| Historia propia | Cambios de 1, 2, 3, 4 y 8 semanas y los dos anteriores; distancia a las medias de 4, 8, 13 y 26 semanas; volatilidad; posición entre el mínimo y el máximo de 26 semanas; rango y asimetría del precio; tendencia del DANE; cambio de la misma semana del año anterior |
| País y región | Cambio y nivel de la mediana nacional; proporción de mercados que suben; diferencia con el país y su desviación de lo habitual; cambio y nivel frente a Corabastos y a la región; cambio del grupo de alimentos |
| Época | Seno y coseno del día del año, y mes |

La relación de cada variable con el cambio siguiente es débil: la más alta es 0,12 (cambio en Corabastos).

## Algoritmo
Promedio de las probabilidades de dos modelos de scikit-learn, con clases balanceadas y semilla 42:
- `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.04, max_leaf_nodes=12, min_samples_leaf=40, l2_regularization=5)`
- `ExtraTreesClassifier(n_estimators=400, max_depth=12, min_samples_leaf=10, max_features=0.4)`, con imputación por mediana

Se eligió con validación hacia adelante, sin usar la prueba. Detalle en [experimentos](09_experimentos.md).

## Resultados en prueba

| | Accuracy | F1 macro | ROC AUC | Ahorro simulado |
|---|---|---|---|---|
| v0.6 | 0,478 | 0,472 | 0,678 | +1,01 % |
| v0.5 (Random Forest) | 0,450 | 0,447 | 0,644 | +0,39 % |
| Persistencia | 0,403 | 0,404 | – | -0,29 % |
| Siempre estable | 0,273 | 0,143 | – | 0 % |
| Comprar todo hoy | 0,340 | 0,169 | – | -0,70 % |

Intervalos de 95 % (remuestreo por semanas): F1 de 0,417 a 0,531; ahorro de 0,38 % a 1,71 %. Frente a la v0.5, el ahorro mejora entre 0,16 y 1,06 puntos; la diferencia de F1 va de -0,028 a +0,078.

**Ahorro simulado:** cuando el modelo dice `sube`, el restaurante compra esta semana; si no, compra la siguiente como siempre. Se compara lo que pagaría con lo que paga normalmente.

## Limitaciones
- El acierto es moderado: más de la mitad de las veces la clase no es la correcta. Por eso cada alerta muestra su confianza.
- La simulación supone que se puede guardar el producto una semana, lo cual no siempre es cierto en perecederos como la lechuga o el cilantro.
- No usa clima ni abastecimiento, que mueven mucho los precios.
- El ahorro que muestra el dashboard para una lista supone que las predicciones se cumplen; en la simulación, el ahorro medio es de 1 %.
- El ahorro simulado no descuenta lo que se daña al guardar un producto una semana.
- El periodo de entrenamiento coincide con una inflación de alimentos particular.

## Estado del monitoreo (22 de noviembre de 2026)
- Acierto de las últimas 8 semanas: 0,444, sobre el mínimo de 0,40. Viene del backtest.
- Hay 20 predicciones reales, todas de la semana del 31 de octubre, y todavía no tienen resultado.

## Monitoreo
El acierto de las últimas 8 semanas y el drift se calculan en cada corrida (ver `docs/05_operacion.md`).
