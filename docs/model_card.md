# Model card: predictor semanal de precios en Cavasa

## Uso previsto
Dar una recomendación de compra semanal (comprar ya, esperar o comprar normal) a restaurantes pequeños de Cali. **No** sirve para fijar precios, negociar contratos ni para mercados distintos a Cavasa sin reentrenar.

## Datos
- Fuentes: boletín semanal de precios mayoristas del SIPSA (DANE) y, desde la v0.7, los precios de cada día de mercado del mismo SIPSA, que llegan por su servicio web.
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
42 numéricas más el producto (one-hot). Ninguna mira al futuro; hay tests que lo comprueban.

| Grupo | Variables |
|---|---|
| Historia propia | Cambios de 1, 2, 3, 4 y 8 semanas y los dos anteriores; distancia a las medias de 4, 8, 13 y 26 semanas; volatilidad; posición entre el mínimo y el máximo de 26 semanas; rango y asimetría del precio; tendencia del DANE; cambio de la misma semana del año anterior |
| País y región | Cambio y nivel de la mediana nacional; proporción de mercados que suben; diferencia con el país y su desviación de lo habitual; cambio y nivel frente a Corabastos y a la región; cambio del grupo de alimentos |
| Época | Seno y coseno del día del año, y mes |
| Cierre de la semana (diario) | Último día de Cavasa frente al precio semanal; jueves frente a lunes; cierre frente al cierre anterior; lo mismo en Corabastos; cierre frente al promedio en la región y en el país; proporción de mercados que subieron dentro de la semana |

Las variables del boletín semanal tienen una relación débil con el cambio siguiente (la más alta es 0,12). Las del diario llegan a 0,33. Cilantro, yuca, papa parda y zanahoria no tienen diario propio en Cavasa: usan solo las de Corabastos, la región y el país.

## Algoritmo
Promedio de las probabilidades de tres familias de modelos de scikit-learn, un voto cada una, con semilla 42:
- `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.04, max_leaf_nodes=12, min_samples_leaf=40, l2_regularization=5)`
- `ExtraTreesClassifier(n_estimators=400, max_depth=12, min_samples_leaf=10, max_features=0.4)`, con imputación por mediana
- Red neuronal `MLPClassifier(hidden_layer_sizes=(32,), alpha=3.0, early_stopping=True)`, con imputación por mediana y escalado por cuantiles. Se promedian cinco semillas, porque una sola red cambia mucho de una corrida a otra

Los dos primeros usan clases balanceadas. La red aporta poco: no sube el F1 y mejora algo el ahorro en validación.

Se eligió con validación hacia adelante, sin usar la prueba. Detalle en [experimentos](09_experimentos.md).

## Resultados en prueba

| | Accuracy | F1 macro | ROC AUC | Ahorro simulado |
|---|---|---|---|---|
| **v0.7 (con el diario y red neuronal)** | **0,540** | **0,533** | **0,729** | **+1,13 %** |
| v0.6 | 0,478 | 0,472 | 0,678 | +1,01 % |
| v0.5 (Random Forest) | 0,450 | 0,447 | 0,644 | +0,39 % |
| Persistencia | 0,403 | 0,404 | – | -0,29 % |
| Siempre estable | 0,273 | 0,143 | – | 0 % |
| Comprar todo hoy | 0,340 | 0,169 | – | -0,70 % |

Otras métricas de la v0.7: balanced accuracy 0,533, kappa de Cohen 0,300, MCC 0,301 y log loss 0,951. Por clase, F1 de 0,59 en `baja`, 0,50 en `estable` y 0,51 en `sube`.

Intervalos de 95 % (remuestreo por semanas): F1 de 0,478 a 0,589; ahorro de 0,3 % a 2,0 %. Frente a la v0.6, el F1 mejora entre 0,029 y 0,095 y el accuracy entre 0,032 y 0,095. El ahorro simulado no cambia de forma distinguible (entre -0,6 y +0,6 puntos).

**Recomendar solo con señal clara.** El dashboard dice "compra ya" o "espera" solo cuando la confianza del modelo es de 50 % o más; en el resto dice "como siempre, sin señal clara". En la prueba eso cubre 54 % de los casos y ahí el acierto es 0,617. Las métricas de la tabla son del modelo opinando sobre todo.

**Ahorro simulado:** cuando el modelo dice `sube`, el restaurante compra esta semana; si no, compra la siguiente como siempre. Se compara lo que pagaría con lo que paga normalmente.

## Limitaciones
- El acierto es moderado: casi la mitad de las veces (46 %) la clase no es la correcta. Por eso solo se recomienda con señal clara, y aun así 4 de cada 10 recomendaciones fallan.
- La simulación supone que se puede guardar el producto una semana, lo cual no siempre es cierto en perecederos como la lechuga o el cilantro.
- No usa clima ni abastecimiento, que mueven mucho los precios.
- Depende del servicio web del DANE para el diario. Si falla, se usa el último descargado y las variables del diario de la semana nueva quedan vacías: el modelo predice igual, pero peor, y la regla de calidad `diario_en_la_ultima_semana` lo avisa.
- Las 20 semanas de prueba ya se habían usado para medir la v0.6.
- El ahorro que muestra el dashboard para una lista supone que las predicciones se cumplen; en la simulación, el ahorro medio es de 1 %.
- El ahorro simulado no descuenta lo que se daña al guardar un producto una semana.
- El periodo de entrenamiento coincide con una inflación de alimentos particular.

## Estado del monitoreo (24 de noviembre de 2026)
- Acierto de las últimas 8 semanas: 0,513, sobre el mínimo de 0,40. Viene del backtest.
- Hay 20 predicciones reales, todas de la semana del 31 de octubre, y todavía no tienen resultado.

## Monitoreo
El acierto de las últimas 8 semanas y el drift se calculan en cada corrida (ver `docs/05_operacion.md`).
