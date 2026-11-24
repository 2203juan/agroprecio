# Fondo animado del pitch

Ocho escenas animadas para proyectar mientras se presenta a dueños de restaurante. No traen texto para leer ni términos técnicos: ilustran lo que dice el [guion](../docs/08_pitch.md).

## Cómo usarlo

Abre `pitch/index.html` en Chrome (doble clic; no necesita internet ni servidor) y pon pantalla completa con `F`.

| Tecla | Qué hace |
|---|---|
| `→`, espacio o clic | Siguiente paso de la escena. Si ya salió todo, pasa a la siguiente escena |
| `S` | Muestra de una vez todo lo que falta de la escena |
| `N` o `Mayús` + `→` | Salta a la siguiente escena |
| `←` | Escena anterior |
| `R` | Repite la escena desde el principio |
| `↑` y `↓` | Más rápido o más lento: 0,5×, 1×, 2× y 4×. La velocidad queda guardada |
| `P` | Pausa y sigue |
| `1` a `8` | Ir a una escena |
| `A` | Modo automático: avanza solo y dura 3:00 a velocidad normal |
| `F` | Pantalla completa |
| `H` | Muestra la lista de teclas |

Las animaciones ya no obligan a esperar. Cada escena entra sola y lo demás aparece al ritmo del guion, pero con `→` adelantas lo que sigue cuando ya terminaste de decirlo. Con `S` queda la escena completa de inmediato.

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
| 8 | Cierre, después de la demostración. El enlace abre la versión en línea | libre |

## Versión en video (opcional)

Si alguna vez hace falta un archivo de video, `node pitch/grabar.mjs` graba las escenas 1 a 7 en un MP4 de 3:00 exactos y el cierre aparte. Necesita Node, Chrome y ffmpeg.

## Si cambian las cifras

Las cifras y los productos de cada grupo están escritos en `index.html`. Corresponden al boletín del 31 de octubre al 6 de noviembre de 2026 y al modelo v0.7. Si llega un boletín nuevo o se reentrena, hay que actualizar la lista `GROUPS`, la lista `WEEKS` y los números de las escenas 4 y 6.

La escena 6 usa el mercado de ejemplo del dashboard: un restaurante de 50 almuerzos diarios de lunes a sábado (222 kilos, unos $696.000 a la semana en promedio). El ahorro es el real de las 20 semanas de prueba, del 16 de mayo al 30 de octubre de 2026: $255.878, y salió mejor en 15 de las 20. Las bolitas siguen el orden real de esas semanas (lista `WEEKS`). Las cifras salen de `ahorro_real` en `GET /lista` con esa lista cargada.
