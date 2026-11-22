# Despliegue en Azure

Se sube solo lo que usa el restaurante: la página y la API, en un único contenedor de Azure App Service. MLflow, Prometheus, Grafana y Airflow se quedan en local.

## Cómo queda

| Pieza | Dónde | Costo |
|---|---|---|
| Imagen (`Dockerfile.nube`): página, API, base SQLite y modelo | `ghcr.io/2203juan/agroprecio` | Gratis |
| Plan `plan-agroprecio` (F1) y app web | App Service, grupo `rg-agroprecio`, West US 3 | Gratis |

Todo vive en `rg-agroprecio`. El plan está en West US 3 porque el plan gratuito no tenía cupo en las otras regiones probadas (East US, East US 2, Central US, West US 2 y South Central US).

Los datos llegan dentro de la imagen. El workflow **Pipeline semanal** corre el pipeline miércoles y sábado, construye la imagen con la base nueva y la publica.

## Qué cambia frente a la versión local

La imagen arranca con `AGRO_PUBLICO=1`:

| En local | En la nube |
|---|---|
| La lista de mercado se guarda en la base | Se guarda en el navegador de cada persona; la API solo calcula los costos |
| Botón *Buscar boletín nuevo* | No aparece y `POST /api/actualizar` responde 403 |
| Las opiniones quedan en la base | Además se copian a `/home/estado/opiniones.jsonl`, la carpeta que App Service conserva, y se recuperan al arrancar |
| nginx sirve la página y reenvía `/api` | `api/publico.py` sirve las dos cosas |

## Primera vez

1. Subir el código a `main`. El workflow publica la imagen.
2. En GitHub, abrir el paquete `agroprecio` → *Package settings* → *Change visibility* → **Public**. Azure la descarga sin credenciales.
3. Crear la app:

```bash
scripts/azure_crear.sh
```

El script imprime la URL. El nombre de la app debe ser único en todo Azure; se cambia con `APP=otro-nombre scripts/azure_crear.sh`.

## Actualización automática

App Service no se entera solo de que hay una imagen nueva. Para que el workflow le avise, se activa el despliegue continuo y se guarda la dirección que entrega como secreto `AZURE_WEBHOOK` del repositorio:

```bash
az webapp deployment container config -n agroprecio -g rg-agroprecio --enable-cd true --query CI_CD_URL -o tsv
```

Esa dirección lleva una credencial: va solo en el secreto, nunca en el código. Sin el secreto, la imagen se publica igual y la app se actualiza reiniciándola:

```bash
az webapp restart -n agroprecio -g rg-agroprecio
```

## Límites del plan gratuito

- **60 minutos de CPU al día.** Si se agotan, la app se detiene hasta el día siguiente. Para un piloto con pocos restaurantes alcanza; el pipeline no corre ahí.
- **Se duerme tras unos 20 minutos sin visitas.** La siguiente carga puede tardar un minuto o más, porque vuelve a arrancar el contenedor. Antes de una demostración hay que abrir la página unos minutos antes.
- 1 GB de memoria (la app usa unos 200 MB) y sin dominio propio.

## Borrar todo

```bash
az group delete -n rg-agroprecio
```

## Límites del aplicativo

- No hay cuentas: la lista es de cada navegador y no pasa de un dispositivo a otro.
- `POST /api/opiniones` es público; cualquiera puede enviar respuestas.
- Una sola instancia. La base SQLite va en el contenedor y no se puede repartir.
