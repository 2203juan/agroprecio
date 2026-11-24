"""Precios diarios del SIPSA, por el servicio web del DANE.

Además del boletín semanal, el DANE publica el precio de cada día de mercado en las
centrales principales. Cavasa tiene mercado lunes y jueves; Corabastos, todos los días.
Sirve para saber cómo terminó la semana frente a su promedio.

El servicio no recibe filtros: una sola petición devuelve toda la historia desde 2020
(unos 300 MB de XML). Por eso se pide como máximo una vez al día y se lee por partes.
"""
import sys
from datetime import date, datetime
from pathlib import Path
from xml.etree.ElementTree import ParseError, iterparse

import pandas as pd
import requests

ENVELOPE = ('<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
            'xmlns:ser="http://servicios.sipsa.co.gov.dane/"><soap:Body>'
            '<ser:promediosSipsaParcial/></soap:Body></soap:Envelope>')
# Campos del servicio que se guardan en bronze, tal como llegan (texto)
FIELDS = ["enmaFecha", "artiNombre", "fuenNombre", "grupNombre", "promedioKg", "minimoKg", "maximoKg"]


def bronze_file(cfg):
    return Path(cfg["paths"]["bronze"]) / "diario" / "sipsa_diario.parquet"


def parse_response(stream):
    """Lee la respuesta sin cargarla entera en memoria. Devuelve una columna por campo."""
    columns = {f: [] for f in FIELDS}
    for _, element in iterparse(stream, events=("end",)):
        if element.tag != "return":
            continue
        values = {child.tag: child.text for child in element}
        for field in FIELDS:
            text = values.get(field)
            # Los nombres se repiten miles de veces: guardamos una sola copia de cada uno
            columns[field].append(sys.intern(text) if text else None)
        element.clear()
    return pd.DataFrame(columns)


def download_daily(cfg, logger):
    """Trae el histórico diario y reemplaza el de bronze. Si el servicio falla o devuelve
    menos datos que antes, se conserva el anterior y el pipeline sigue."""
    path = bronze_file(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and date.fromtimestamp(path.stat().st_mtime) == date.today():
        logger.info("El diario del SIPSA ya se descargó hoy")
        return False
    try:
        resp = requests.post(cfg["source"]["daily_ws_url"], data=ENVELOPE, stream=True, timeout=(30, 900),
                             headers={"Content-Type": "application/soap+xml; charset=utf-8"})
        resp.raise_for_status()
        resp.raw.decode_content = True
        raw = parse_response(resp.raw)
    except (requests.RequestException, ParseError) as error:
        logger.warning("No se pudo descargar el diario del SIPSA (%s). Se usa el anterior.", error)
        return False

    previous = len(pd.read_parquet(path, columns=["enmaFecha"])) if path.exists() else 0
    if len(raw) < previous * 0.9 or raw.empty:
        logger.warning("El diario llegó incompleto (%s filas, antes %s). Se conserva el anterior.", len(raw), previous)
        return False
    raw.to_parquet(path, index=False)
    days = raw["enmaFecha"].str[:10]
    log_row = pd.DataFrame([{"descarga": datetime.now().isoformat(timespec="seconds"), "filas": len(raw),
                             "desde": days.min(), "hasta": days.max(), "url": cfg["source"]["daily_ws_url"]}])
    manifest = path.with_name("descargas.csv")
    log_row.to_csv(manifest, mode="a", header=not manifest.exists(), index=False)
    logger.info("Diario del SIPSA: %s filas, del %s al %s", len(raw), days.min(), days.max())
    return True


def extract_daily(cfg):
    """El diario de bronze, o None si todavía no se ha descargado."""
    path = bronze_file(cfg)
    return pd.read_parquet(path) if path.exists() else None
