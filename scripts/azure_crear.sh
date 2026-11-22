#!/usr/bin/env bash
# Crea AgroPrecio en Azure App Service (plan gratuito). Se corre una sola vez, con
# `az login` hecho y la imagen ya publicada en ghcr.io por el workflow "Pipeline semanal".
#
#   scripts/azure_crear.sh
#
# Variables opcionales: RG, PLAN, APP (debe ser única en todo Azure), REGION e IMAGEN.
set -euo pipefail

RG=${RG:-rg-agroprecio}
PLAN=${PLAN:-plan-agroprecio}
APP=${APP:-agroprecio}
# El plan gratuito no tiene cupo en todas las regiones: en esta suscripción lo hubo en westus3
REGION=${REGION:-westus3}
IMAGEN=${IMAGEN:-ghcr.io/2203juan/agroprecio:latest}

az group create -n "$RG" -l "$REGION" --tags proyecto=agroprecio --only-show-errors >/dev/null 2>&1 || true
if ! az appservice plan show -n "$PLAN" -g "$RG" --only-show-errors >/dev/null 2>&1; then
  az appservice plan create -n "$PLAN" -g "$RG" -l "$REGION" --is-linux --sku F1 --only-show-errors >/dev/null
fi

if ! az webapp show -n "$APP" -g "$RG" --only-show-errors >/dev/null 2>&1; then
  az webapp create -n "$APP" -g "$RG" -p "$PLAN" --container-image-name "$IMAGEN" --https-only true --only-show-errors >/dev/null
fi

# /home es lo único que sobrevive a los reinicios: ahí van las respuestas de "¿Te sirvió?"
az webapp config appsettings set -n "$APP" -g "$RG" --only-show-errors --settings \
  WEBSITES_PORT=8000 \
  WEBSITES_ENABLE_APP_SERVICE_STORAGE=true \
  WEBSITES_CONTAINER_START_TIME_LIMIT=600 \
  AGRO_ESTADO=/home/estado >/dev/null
az webapp config set -n "$APP" -g "$RG" --ftps-state Disabled --min-tls-version 1.2 --only-show-errors >/dev/null

echo "https://$(az webapp show -n "$APP" -g "$RG" --query defaultHostName -o tsv)"
