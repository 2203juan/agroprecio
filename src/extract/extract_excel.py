"""Descarga y lectura de los boletines semanales del SIPSA (capa bronze)."""
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (agroprecio)"}

# Hojas con precios por kilo. La 1.9 es arroz en molino (por tonelada) y
# la 1.10 es abastecimiento, así que no las usamos.
PRICE_SHEETS = ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"]

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}


def list_bulletins(cfg):
    """Devuelve la lista de boletines publicados: [{doc_id, title}, ...]."""
    page = requests.get(cfg["source"]["listing_url"], headers=HEADERS, timeout=60).text
    context = re.search(r'data-ajax-context="([^"]+)"', page).group(1)
    module_id = re.search(r'data-module-id="(\d+)"', page).group(1)

    bulletins = {}
    page_number = 1
    while True:
        body = {
            "module_id": module_id, "source_id": "2", "context": context,
            "page": page_number, "per_page": 10, "sort": "recent",
            "year": "", "month": "", "day": "",
        }
        resp = requests.post(
            cfg["source"]["ajax_url"], data=body, timeout=60,
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
        )
        html = resp.json()["data"]["html"]
        found = re.findall(r'DOC-(\d+)/anexos"[^>]*aria-label="([^",]+)', html)
        new = [(d, t) for d, t in found if d not in bulletins]
        if not new:
            break
        for doc_id, title in new:
            bulletins[doc_id] = title.strip()
        page_number += 1

    return [{"doc_id": d, "title": t} for d, t in bulletins.items()]


def download_bulletins(cfg, logger, limit=None):
    """Descarga a bronze los boletines que todavía no tenemos.

    Guarda un manifest.csv con el origen de cada archivo para poder
    rastrear de dónde viene cada dato.
    """
    bronze = Path(cfg["paths"]["bronze"])
    bronze.mkdir(parents=True, exist_ok=True)
    manifest_path = bronze / "manifest.csv"
    manifest = pd.read_csv(manifest_path, dtype=str) if manifest_path.exists() else pd.DataFrame()

    bulletins = list_bulletins(cfg)
    logger.info("Boletines publicados en el DANE: %s", len(bulletins))
    if limit:
        bulletins = bulletins[:limit]

    max_bytes = cfg["source"]["max_file_mb"] * 1024 * 1024
    rows = []
    for b in bulletins:
        path = bronze / f"sipsa_{b['doc_id']}.xlsx"
        if path.exists():
            continue
        url = cfg["source"]["file_url"].format(doc_id=b["doc_id"])
        resp = requests.get(url, headers=HEADERS, timeout=120)
        if resp.status_code != 200 or len(resp.content) > max_bytes:
            logger.warning("Se omite %s (%s, %s bytes)", b["title"], resp.status_code, len(resp.content))
            continue
        path.write_bytes(resp.content)
        rows.append({
            "doc_id": b["doc_id"], "title": b["title"], "file": path.name,
            "url": url, "bytes": len(resp.content),
            "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        })
        logger.info("Descargado %s", b["title"])
        time.sleep(0.5)

    if rows:
        manifest = pd.concat([manifest, pd.DataFrame(rows)], ignore_index=True)
        manifest.to_csv(manifest_path, index=False)
    logger.info("Archivos nuevos en bronze: %s", len(rows))
    return len(rows)


def parse_week(title):
    """'Boletín semanal precios mayoristas - 31 de octubre al 6 de noviembre de 2026'
    -> (fecha_inicio, fecha_fin). El año solo aparece al final."""
    text = title.lower()
    m = re.search(r"(\d{1,2})\s*(?:de\s+)?([a-z]+)?\s*(?:de\s+(\d{4}))?\s*al?\s+(\d{1,2})\s*de\s*([a-z]+)\s*(?:de|del)?\s*(\d{4})", text)
    if not m:
        return None, None
    d1, m1, y1, d2, m2, y2 = m.groups()
    month_end = MONTHS[m2]
    month_start = MONTHS.get(m1, month_end) if m1 else month_end
    year_end = int(y2)
    year_start = int(y1) if y1 else (year_end - 1 if month_start > month_end else year_end)
    return (
        pd.Timestamp(year_start, month_start, int(d1)),
        pd.Timestamp(year_end, month_end, int(d2)),
    )


def read_bulletin(path):
    """Lee un boletín y devuelve una tabla larga con los precios tal como vienen."""
    xls = pd.ExcelFile(path)
    index = pd.read_excel(xls, sheet_name=0, header=None)
    title = next(
        str(v) for v in index.iloc[:, 0].dropna()
        if "boletín semanal" in str(v).lower() or "boletin semanal" in str(v).lower()
    )
    start, end = parse_week(title)

    frames = []
    for sheet in PRICE_SHEETS:
        if sheet not in xls.sheet_names:
            continue
        raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        group = str(raw.iloc[5, 0]).split(". ", 1)[-1].replace("*", "").strip()
        header_row = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Producto"][0]
        data = raw.iloc[header_row + 2:, :6].copy()
        data.columns = ["producto", "mercado", "precio_min", "precio_max", "precio_medio", "tendencia"]
        data = data.dropna(subset=["producto", "mercado"])
        data["grupo"] = group
        frames.append(data)

    xls.close()

    df = pd.concat(frames, ignore_index=True)
    df["semana_inicio"] = start
    df["semana_fin"] = end
    df["archivo"] = Path(path).name
    return df


def extract_all(cfg, logger):
    """Lee los Excel de bronze uno por uno, para no tenerlos todos en memoria sin limpiar.
    Si un archivo no se puede leer, se registra y se sigue."""
    files = sorted(Path(cfg["paths"]["bronze"]).glob("sipsa_*.xlsx"))
    read = 0
    for f in files:
        try:
            bulletin = read_bulletin(f)
        except Exception as e:
            logger.warning("No se pudo leer %s: %s", f.name, e)
            continue
        read += 1
        yield bulletin
    logger.info("Boletines leídos: %s de %s", read, len(files))
