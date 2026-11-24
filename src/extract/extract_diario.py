"""Precios diarios del SIPSA, por el servicio web del DANE.

Además del boletín semanal, el DANE publica el precio de cada día de mercado en las
centrales principales. Cavasa tiene mercado lunes y jueves; Corabastos, todos los días.
Sirve para saber cómo terminó la semana frente a su promedio.

El servicio no recibe filtros: una sola petición devuelve toda la historia desde 2020
(unos 300 MB de XML). Por eso se pide como máximo una vez al día y se lee por partes.

El servicio no responde desde fuera de Colombia (por ejemplo, desde GitHub Actions). Para
ese caso hay un respaldo: se parte de una copia guardada en el repositorio y se agregan los
días que falten con el anexo diario en Excel, que está en el sitio principal del DANE y
trae los mismos precios.
"""
import shutil
import sys
import time
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from xml.etree.ElementTree import ParseError, iterparse

import pandas as pd
import requests
from openpyxl import load_workbook

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


MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
# El Excel abrevia algunos mercados; aquí quedan con el nombre del servicio web
EXCEL_MARKETS = {
    "Bogotá, Corabastos": "Bogotá, D.C., Corabastos",
    "Medellín, CMA": "Medellín, Central Mayorista de Antioquia",
    "Popayán": "Popayán, Plaza de mercado del barrio Bolívar",
    "Santa Marta": "Santa Marta (Magdalena)",
    "Tunja": "Tunja, Complejo de Servicios del Sur",
}


def read_excel_day(content, day):
    """Un anexo diario en Excel, con las mismas columnas (y todo como texto) que el servicio web.
    El Excel solo trae el precio promedio: mínimo y máximo quedan iguales a él."""
    rows = list(load_workbook(content, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    head = next(i for i, r in enumerate(rows) if r and r[0] and "Precio" in str(r[0]))
    # Cada mercado ocupa dos columnas: precio y variación
    markets = {j: " ".join(str(name).split()) for j, name in enumerate(rows[head]) if j > 0 and name}
    out, group = [], None
    for row in rows[head + 2:]:
        if not row or not row[0]:
            continue
        if all(v is None for v in row[1:]):
            group = str(row[0]).strip().upper()  # título de grupo (o nota al pie)
            continue
        for j, market in markets.items():
            price = row[j] if j < len(row) else None
            if isinstance(price, (int, float)) and price > 0:
                text = str(round(price))
                out.append({"enmaFecha": f"{day.date()}T00:00:00-05:00", "artiNombre": str(row[0]).strip(),
                            "fuenNombre": EXCEL_MARKETS.get(market, market), "grupNombre": group,
                            "promedioKg": text, "minimoKg": text, "maximoKg": text})
    return pd.DataFrame(out, columns=FIELDS)


def update_from_excel(cfg, logger, today=None, pause=2.0):
    """Respaldo: agrega a bronze los días hábiles posteriores al último que hay, bajando el
    anexo de cada día. Son pocos archivos; si el DANE limita las descargas, se detiene."""
    path = bronze_file(cfg)
    if not path.exists():
        return 0
    raw = pd.read_parquet(path)
    last = pd.Timestamp(raw["enmaFecha"].str[:10].max())
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (AgroPrecio; proyecto académico)"
    new = []
    for day in pd.bdate_range(last + pd.Timedelta(days=1), today):
        url = cfg["source"]["daily_excel_url"].format(day=f"{day.day:02d}", month=MONTHS[day.month - 1], year=day.year)
        try:
            resp = session.get(url, timeout=60)
        except requests.RequestException as error:
            logger.warning("No se pudo bajar el anexo diario del %s (%s)", day.date(), error)
            break
        if resp.status_code == 429:
            logger.warning("El DANE limitó las descargas del anexo diario; se continúa en la próxima corrida")
            break
        if resp.status_code == 200 and resp.content.startswith(b"PK"):  # 404 en festivos
            new.append(read_excel_day(BytesIO(resp.content), day))
        time.sleep(pause)
    if new:
        pd.concat([raw, *new], ignore_index=True).to_parquet(path, index=False)
    logger.info("Diario del SIPSA por Excel: %s días nuevos desde el %s", len(new), last.date())
    return len(new)


def use_seed(cfg, logger):
    """Si bronze no tiene el diario, o el del repositorio es más reciente, parte de ese."""
    path, seed = bronze_file(cfg), Path(cfg["source"].get("daily_seed", ""))
    if not seed.is_file():
        return
    newest = lambda p: pd.read_parquet(p, columns=["enmaFecha"])["enmaFecha"].str[:10].max()
    if not path.exists() or newest(seed) > newest(path):
        shutil.copyfile(seed, path)
        logger.info("Diario del SIPSA: se parte de la copia del repositorio (%s)", seed)


def download_daily(cfg, logger):
    """Trae el histórico diario y reemplaza el de bronze. Si el servicio falla o devuelve
    menos datos que antes, se conserva lo que hay y se completa con los anexos en Excel."""
    path = bronze_file(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and date.fromtimestamp(path.stat().st_mtime) == date.today():
        logger.info("El diario del SIPSA ya se descargó hoy")
        return False
    use_seed(cfg, logger)
    try:
        resp = requests.post(cfg["source"]["daily_ws_url"], data=ENVELOPE, stream=True, timeout=(30, 900),
                             headers={"Content-Type": "application/soap+xml; charset=utf-8"})
        resp.raise_for_status()
        resp.raw.decode_content = True
        raw = parse_response(resp.raw)
    except (requests.RequestException, ParseError) as error:
        logger.warning("El servicio web del SIPSA no respondió (%s). Se completa con los anexos en Excel.",
                       type(error).__name__)
        return update_from_excel(cfg, logger) > 0

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
