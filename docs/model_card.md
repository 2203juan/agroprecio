# Model card: predictor semanal de precios en Cavasa

## Uso previsto
Dar una recomendación de compra semanal (comprar ya, esperar o comprar normal) a restaurantes pequeños de Cali. **No** sirve para fijar precios, negociar contratos ni para mercados distintos a Cavasa sin reentrenar.

## Datos
- Fuente: boletín semanal de precios mayoristas del SIPSA (DANE).
- Mercado: Cali, Cavasa. Productos: los 20 de `config/config.yaml`.
- Periodo: de mayo de 2023 a octubre de 2026, unas 3.400 semanas-producto con objetivo.
- Entrenamiento: hasta 20 semanas antes del final. Prueba: las últimas 20 semanas (400 filas).

## Objetivo
Cambio del precio medio la semana siguiente:
- `sube` si es mayor a +3 %
- `baja` si es menor a -3 %
- `estable` si queda en medio

Distribución: 36 % baja, 36 % sube y 28 % estable.

## Variables
| Variable | Descripción |
|---|---|
| `producto` | One-hot del producto |
| `cambio_1s`, `cambio_2s`, `cambio_4s` | Cambio de precio contra 1, 2 y 4 semanas atrás |
| `vs_media_4s` | Precio actual contra la media de las últimas 4 semanas |
| `vs_nacional` | Precio de Cavasa contra la mediana de todos los mercados |
| `cambio_nacional_1s` | Cambio semanal de la mediana nacional |
| `mes` | Mes del año |

Las tres variables más importantes son `cambio_nacional_1s`, `cambio_1s` y `vs_nacional`. Eso apoya la hipótesis de que Cavasa sigue con rezago lo que pasa en el resto del país.

## Algoritmo
`RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=5, class_weight="balanced", random_state=42)`. No hubo búsqueda de hiperparámetros.

## Resultados en prueba

| | Accuracy | F1 macro | Ahorro simulado |
|---|---|---|---|
| Random Forest | 0,45 | 0,45 | +0,4 % |
| Persistencia | 0,40 | 0,40 | -0,3 % |
| Siempre estable | 0,27 | 0,14 | 0 % |

**Ahorro simulado:** cuando el modelo dice `sube`, el restaurante compra esta semana; si no, compra la siguiente como siempre. Se compara lo que pagaría con lo que paga normalmente.

## Limitaciones
- El acierto es moderado: más de la mitad de las veces la clase no es la correcta. Por eso cada alerta muestra su confianza.
- La simulación supone que se puede guardar el producto una semana, lo cual no siempre es cierto en perecederos como la lechuga o el cilantro.
- No usa clima ni abastecimiento, que mueven mucho los precios.
- El periodo de entrenamiento coincide con una inflación de alimentos particular.

## Monitoreo
El acierto de las últimas 8 semanas y el drift se calculan en cada corrida (ver `docs/05_operacion.md`).
