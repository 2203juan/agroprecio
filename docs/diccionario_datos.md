# Diccionario de datos

## Bronze: boletín semanal del SIPSA

Un Excel por semana con un índice y nueve hojas. Se usan las hojas 1.1 a 1.8, con precios en pesos por kilo:

| Hoja | Grupo |
|---|---|
| 1.1 | Verduras y hortalizas |
| 1.2 | Frutas frescas |
| 1.3 | Tubérculos, raíces y plátanos |
| 1.4 | Granos y cereales |
| 1.5 | Huevos y lácteos |
| 1.6 | Carnes |
| 1.7 | Pescados |
| 1.8 | Productos procesados |

La 1.9 (arroz en molino, por tonelada) y la 1.10 (abastecimiento) no se usan todavía.

La semana se toma del título del índice, por ejemplo "Boletín semanal precios mayoristas - 31 de octubre al 6 de noviembre de 2026". Las semanas empiezan en sábado. En festivos el boletín cubre menos días, pero la semana empieza igual en sábado.

`manifest.csv`: `doc_id`, `title`, `file`, `url`, `bytes`, `downloaded_at`.

## Bronze: precios diarios del SIPSA

`data/bronze/diario/sipsa_diario.parquet`: la respuesta del servicio web del DANE (`promediosSipsaParcial`), tal como llega y como texto. Una fila por día, producto y mercado, desde febrero de 2020; unas 714 mil filas. Se reemplaza completa, como máximo una vez al día, porque el servicio no recibe filtros.

| Columna | Descripción |
|---|---|
| `enmaFecha` | Día de mercado |
| `artiNombre` | Producto. El asterisco marca "variedad predominante en el mercado" |
| `fuenNombre` | Central mayorista (26) |
| `grupNombre` | Grupo de alimentos |
| `promedioKg`, `minimoKg`, `maximoKg` | Pesos por kilo |

`descargas.csv` guarda la fecha de cada descarga, las filas y el rango de días.

Cavasa tiene mercado lunes y jueves; Corabastos, de lunes a viernes. Trae unos 37 productos: no incluye cilantro, y la yuca, la papa parda y la zanahoria de Cavasa no corresponden a las del boletín semanal.

## Silver: `data/silver/diario.parquet`

`fecha`, `producto`, `mercado`, `precio`, `precio_min` y `precio_max`, con nombres limpios, precios numéricos mayores que cero y sin duplicados. Llave: (`fecha`, `producto`, `mercado`).

## Silver: `data/silver/precios.parquet`

Los textos se guardan como categorías para ocupar menos memoria.

| Columna | Tipo | Descripción |
|---|---|---|
| `semana_inicio` | fecha | Sábado en que empieza la semana del boletín |
| `semana_fin` | fecha | Último día que cubre el boletín |
| `anio` | entero | Año de `semana_inicio` |
| `grupo` | texto | Grupo de alimentos |
| `producto` | texto | Nombre del producto según el SIPSA |
| `mercado` | texto | Central o plaza mayorista |
| `precio_min`, `precio_max`, `precio_medio` | número | Pesos por kilo |
| `tendencia` | texto | Tendencia que reporta el DANE (`+`, `++`, `-`, `=`, …) |
| `archivo` | texto | Archivo de bronze de donde salió la fila |

Llave: (`semana_inicio`, `producto`, `mercado`).

## Gold: `data/gold/features.parquet` y tabla `features`

| Columna | Descripción |
|---|---|
| `producto`, `grupo`, `semana_inicio` | Llave y grupo |
| `precio` | Precio medio en Cavasa |
| `precio_nacional` | Mediana del precio medio en todos los mercados |
| 42 columnas numéricas | Variables del modelo: `OWN`, `MARKET` y `SEASON` en `src/transform/gold_transformations.py`, y las nueve del diario (`DAILY_FEATURES`) en `src/transform/diario.py`. Están descritas en la [model card](model_card.md) |
| `precio_siguiente` | Precio de la semana siguiente (vacío si esa semana no existe) |
| `cambio_siguiente` | Cambio porcentual hacia la semana siguiente |
| `clase` | `sube`, `baja` o `estable` |

`data/gold/entrenamiento.parquet` tiene las mismas columnas y `mercado`, para Cavasa y Santa Elena. Solo se usa para entrenar.

## Otras tablas en `agroprecio.db`

| Tabla | Contenido |
|---|---|
| `precios_cali` | Silver filtrado a los mercados de Cali |
| `alertas` | Predicción (`prediccion`, la clase del modelo), `confianza`, `senal` (`clara` o `debil` según `model.min_confidence`), `recomendacion` (la predicción si la señal es clara; si no, `estable`) y acción de la última semana por producto, con el rango de precio esperado (`precio_min_esperado`, `precio_max_esperado`: percentiles 25 y 75 del cambio histórico del producto en esa misma clase) y los aciertos del modelo con ese producto en sus últimas 8 semanas evaluadas (`aciertos`, `evaluadas`) |
| `listas` | Lista de mercado del restaurante: `restaurante`, `producto`, `kg_semana`. La escribe la API desde el dashboard |
| `predicciones` | Historial de predicciones con la versión del modelo y la `recomendacion` que se mostró. Las del backtest no tienen `confianza` |
| `accuracy_semanal` | Acierto por semana y cuántas de las predicciones son reales |
| `drift` | Z-score del último cambio por producto |
| `monitoreo` | Resumen por corrida y bandera de reentrenamiento. `accuracy_ultimas_8_semanas` incluye backtest; `predicciones_reales` y `accuracy_real` no |
| `opiniones` | Respuesta a "¿te sirvió?": `fecha`, `semana_inicio`, `restaurante`, `util` (1 o 0) y `comentario` |
| `calidad_datos` | Resultado de cada regla de calidad por corrida |
| `boletines` | Texto del boletín, fuente (Claude o plantilla) y semana |

## Problemas conocidos de la fuente
- El DANE publica con rezago: puede no haber boletín nuevo por varias semanas.
- Faltan 3 semanas en el histórico disponible.
- Un boletín (29 ago - 4 sep de 2026) pesa 24 MB y se omite por el límite de tamaño de la descarga.
- Algunos productos aparecen repetidos dentro del mismo boletín; se deja la primera fila.
- El título de la semana no tiene un formato fijo ("al" o "a", con o sin año en la primera fecha).
