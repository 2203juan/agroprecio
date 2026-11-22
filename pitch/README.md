# Fondo animado del pitch

Ocho escenas animadas para proyectar mientras se presenta a dueños de restaurante. No traen texto para leer ni términos técnicos: ilustran lo que dice el [guion](../docs/08_pitch.md).

## Cómo usarlo

Abre `pitch/index.html` en Chrome (doble clic; no necesita internet ni servidor) y pon pantalla completa con `F`.

| Tecla | Qué hace |
|---|---|
| `→`, espacio o clic | Siguiente escena |
| `←` | Escena anterior |
| `1` a `8` | Ir a una escena |
| `A` | Modo automático: avanza solo y dura 3:00 |
| `F` | Pantalla completa |

Los pasadores de diapositivas también funcionan, porque envían `Page Down` y `Page Up`.

Cada escena queda en bucle hasta que avanzas, así que no hay que correr detrás del video. La barra de abajo se llena en el tiempo previsto para esa escena.

| # | Escena | Tiempo |
|---|---|---|
| 1 | Portada | 0:06 |
| 2 | Comprar a ciegas | 0:29 |
| 3 | 4.000 filas de Excel | 0:30 |
| 4 | ¿Qué compro ya y qué espero? | 0:30 |
| 5 | Fácil, cada semana | 0:30 |
| 6 | ¿Cuánto me ahorro? | 0:30 |
| 7 | ¿Lo probamos? | 0:25 |
| 8 | Cierre, después de la demostración | libre |

## Versión en video (opcional)

Si alguna vez hace falta un archivo de video, `node pitch/grabar.mjs` graba las escenas 1 a 7 en un MP4 de 3:00 exactos y el cierre aparte. Necesita Node, Chrome y ffmpeg.

## Si cambian las cifras

Las cifras y los productos de cada grupo están escritos en `index.html`. Corresponden al boletín del 31 de octubre al 6 de noviembre de 2026 y al modelo v0.6. Si llega un boletín nuevo o se reentrena, hay que actualizar la lista `GROUPS` y los números de las escenas 4 y 6.

El ahorro de la escena 6 es un ejemplo: 1 % de un mercado de $1.000.000 a la semana, por 52 semanas. El 1 % es el ahorro simulado del modelo, que va de 0,4 % a 1,7 %.
