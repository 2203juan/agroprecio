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

## Silver: `data/silver/precios.parquet`

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
| `cambio_1s`, `cambio_2s`, `cambio_4s`, `vs_media_4s`, `vs_nacional`, `cambio_nacional_1s`, `mes` | Variables del modelo |
| `precio_siguiente` | Precio de la semana siguiente (vacío si esa semana no existe) |
| `cambio_siguiente` | Cambio porcentual hacia la semana siguiente |
| `clase` | `sube`, `baja` o `estable` |

## Otras tablas en `agroprecio.db`

| Tabla | Contenido |
|---|---|
| `precios_cali` | Silver filtrado a los mercados de Cali |
| `alertas` | Predicción y acción de la última semana por producto |
| `predicciones` | Historial de predicciones con la versión del modelo |
| `accuracy_semanal` | Acierto por semana |
| `drift` | Z-score del último cambio por producto |
| `monitoreo` | Resumen por corrida y bandera de reentrenamiento |
| `calidad_datos` | Resultado de cada regla de calidad por corrida |
| `boletines` | Texto del boletín, fuente (Claude o plantilla) y semana |

## Problemas conocidos de la fuente
- Faltan 3 semanas en el histórico disponible.
- Un boletín (29 ago - 4 sep de 2026) pesa 24 MB y se omite por el límite de tamaño de la descarga.
- Algunos productos aparecen repetidos dentro del mismo boletín; se deja la primera fila.
- El título de la semana no tiene un formato fijo ("al" o "a", con o sin año en la primera fecha).
