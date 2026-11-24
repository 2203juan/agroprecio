import io
import logging
import os

import pandas as pd
import pytest
import requests

import main
from src.extract import extract_diario
from src.extract.extract_diario import download_daily, parse_response
from src.quality import daily_coverage
from src.transform.diario import DAILY_FEATURES, add_daily_features, clean_daily, week_start
from src.transform.gold_transformations import FEATURES, build_gold, build_panel
from tests.conftest import PRODUCTS, raw_daily

LOG = logging.getLogger("test")
XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope"><S:Body>
<ns2:promediosSipsaParcialResponse xmlns:ns2="http://servicios.sipsa.co.gov.dane/">
<return><artiNombre>Tomate*</artiNombre><enmaFecha>2026-11-19T00:00:00-05:00</enmaFecha><fuenId>7</fuenId>
<fuenNombre>Cali,  Cavasa</fuenNombre><grupNombre>VERDURAS Y HORTALIZAS</grupNombre>
<maximoKg>3900</maximoKg><minimoKg>3500</minimoKg><promedioKg>3700</promedioKg></return>
<return><artiNombre>Lulo</artiNombre><enmaFecha>2026-11-19T00:00:00-05:00</enmaFecha>
<fuenNombre>Cali, Santa Helena</fuenNombre><grupNombre>FRUTAS</grupNombre>
<maximoKg>0</maximoKg><minimoKg>0</minimoKg><promedioKg>0</promedioKg></return>
</ns2:promediosSipsaParcialResponse></S:Body></S:Envelope>"""


def test_parse_response_keeps_the_raw_text():
    raw = parse_response(io.BytesIO(XML))
    assert len(raw) == 2
    assert raw.loc[0, "artiNombre"] == "Tomate*" and raw.loc[0, "promedioKg"] == "3700"


def test_clean_daily_fixes_names_and_drops_empty_prices():
    daily = clean_daily(parse_response(io.BytesIO(XML)))
    assert daily[["producto", "mercado", "precio"]].values.tolist() == [["Tomate", "Cali, Cavasa", 3700.0]]
    assert daily.loc[0, "fecha"] == pd.Timestamp("2026-11-19")


def test_week_starts_on_saturday():
    days = pd.Series(pd.to_datetime(["2026-11-14", "2026-11-16", "2026-11-19", "2026-11-20", "2026-11-21"]))
    assert week_start(days).dt.strftime("%Y-%m-%d").tolist() == ["2026-11-14"] * 4 + ["2026-11-21"]


def test_daily_features_compare_the_close_with_the_week(silver):
    weeks = pd.date_range("2026-01-03", periods=20, freq="7D")
    daily = clean_daily(raw_daily(weeks))
    gold = build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03, daily)
    tomato = gold[gold["producto"] == "Tomate chonto"]
    # Lunes 0,98 y jueves 1,02 del precio base: el cierre queda 4 % por encima del lunes
    assert tomato["dia_cambio_intra"].round(2).eq(0.04).all()
    assert tomato["cora_cambio_intra"].round(2).eq(0.04).all()
    assert tomato["dia_ultimo_vs_semana"].notna().all()
    # El diario no trae cilantro: sus variables quedan vacías y el modelo lo admite
    assert gold.loc[gold["producto"] == "Cilantro", DAILY_FEATURES].isna().all().all()


def test_daily_features_do_not_look_into_the_future(silver):
    """Quitar los últimos días no cambia las variables de las semanas anteriores."""
    weeks = pd.date_range("2026-01-03", periods=20, freq="7D")
    daily = clean_daily(raw_daily(weeks))
    cut = weeks[14]
    key = ["mercado", "producto", "semana_inicio"]
    full = build_panel(silver, "Cali, Cavasa", PRODUCTS, 0.03, daily)
    full = full[full["semana_inicio"] < cut].set_index(key)[FEATURES].sort_index()
    past = build_panel(silver[silver["semana_inicio"] < cut], "Cali, Cavasa", PRODUCTS, 0.03,
                       daily[daily["fecha"] < cut])
    pd.testing.assert_frame_equal(full, past.set_index(key)[FEATURES].sort_index())


def test_without_daily_the_features_are_empty(silver):
    panel = add_daily_features(build_panel(silver, "Cali, Cavasa", PRODUCTS, 0.03)[["mercado", "producto", "semana_inicio", "precio"]], None)
    assert panel[DAILY_FEATURES].isna().all().all()
    assert daily_coverage(build_gold(silver, "Cali, Cavasa", PRODUCTS, 0.03)) == 0


class FakeSession:
    """Sitio del DANE de mentira: responde lo que se le diga para cada día."""
    def __init__(self, answers):
        self.answers, self.headers, self.asked = answers, {}, []

    def get(self, url, timeout=None):
        self.asked.append(url)
        status, content = self.answers.get(url.rsplit("-", 1)[1], (404, b""))
        return type("Resp", (), {"status_code": status, "content": content})()


def excel_day(prices):
    """Anexo diario con la forma del DANE: dos columnas por mercado."""
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append([None]); ws.append(["Jueves 19 de noviembre de 2026"])
    ws.append(["Precio $/Kg", "Cali,  Cavasa", None, "Bogotá, Corabastos", None])
    ws.append([None, "Precio", "Var %", "Precio", "Var %"])
    ws.append(["Verduras y hortalizas", None, None, None, None])
    for product, (cali, bogota) in prices.items():
        ws.append([product, cali, 0.01, bogota, "n.d."])
    ws.append(["*Variedad predominante en el mercado", None, None, None, None])
    out = io.BytesIO(); wb.save(out)
    return out.getvalue()


def offline(cfg, monkeypatch, answers):
    """Sin servicio web y con el sitio del DANE de mentira."""
    cfg["source"] = {"daily_ws_url": "https://example.invalid/ws", "daily_seed": "no-existe.parquet",
                     "daily_excel_url": "https://example.invalid/anex-{day}{month}{year}.xlsx"}
    def fail(*args, **kwargs):
        raise requests.ConnectionError("sin red")
    session = FakeSession(answers)
    monkeypatch.setattr(extract_diario.requests, "post", fail)
    monkeypatch.setattr(extract_diario.requests, "Session", lambda: session)
    monkeypatch.setattr(extract_diario.time, "sleep", lambda s: None)
    return session


def old_bronze(cfg, last="2026-11-18"):
    """Un diario en bronze que llega hasta `last` y se descargó otro día."""
    path = extract_diario.bronze_file(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = raw_daily(pd.date_range("2026-10-31", periods=3, freq="7D"))
    raw[raw["enmaFecha"].str[:10] <= last].to_parquet(path)
    stamp = pd.Timestamp("2026-01-01").timestamp()
    os.utime(path, (stamp, stamp))
    return path


def test_excel_day_has_the_same_shape_as_the_web_service():
    day = extract_diario.read_excel_day(io.BytesIO(excel_day({"Tomate*": (3700, 2900), "Lulo": ("n.d.", 4100)})),
                                        pd.Timestamp("2026-11-19"))
    assert list(day.columns) == extract_diario.FIELDS and len(day) == 3
    clean = clean_daily(day)
    assert clean[["producto", "mercado", "precio"]].values.tolist() == [
        ["Lulo", "Bogotá, D.C., Corabastos", 4100.0], ["Tomate", "Bogotá, D.C., Corabastos", 2900.0],
        ["Tomate", "Cali, Cavasa", 3700.0]]


def test_without_the_web_service_new_days_come_from_excel(cfg, monkeypatch):
    path = old_bronze(cfg, last="2026-11-18")
    before = len(pd.read_parquet(path))
    session = offline(cfg, monkeypatch, {"19nov2026.xlsx": (200, excel_day({"Tomate*": (3700, 2900)}))})
    monkeypatch.setattr(extract_diario.pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-11-20")))
    assert download_daily(cfg, LOG) is True
    raw = pd.read_parquet(path)
    assert len(raw) == before + 2 and raw["enmaFecha"].str[:10].max() == "2026-11-19"
    assert [u.rsplit("-", 1)[1] for u in session.asked] == ["19nov2026.xlsx", "20nov2026.xlsx"]  # el 20 no existe


def test_rate_limit_stops_the_excel_update(cfg, monkeypatch):
    path = old_bronze(cfg, last="2026-11-18")
    before = len(pd.read_parquet(path))
    session = offline(cfg, monkeypatch, {"19nov2026.xlsx": (429, b"")})
    monkeypatch.setattr(extract_diario.pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-11-24")))
    assert download_daily(cfg, LOG) is False
    assert len(pd.read_parquet(path)) == before and len(session.asked) == 1


def test_seed_is_used_when_bronze_is_empty_or_older(cfg, tmp_path):
    seed = tmp_path / "semilla.parquet"
    raw_daily(pd.date_range("2026-10-31", periods=3, freq="7D")).to_parquet(seed)
    cfg["source"] = {"daily_seed": str(seed)}
    path = extract_diario.bronze_file(cfg)
    path.parent.mkdir(parents=True)
    extract_diario.use_seed(cfg, LOG)
    assert len(pd.read_parquet(path)) == len(pd.read_parquet(seed))
    # Un bronze más reciente que la copia no se pisa
    newer = raw_daily(pd.date_range("2026-10-31", periods=5, freq="7D"))
    newer.to_parquet(path)
    extract_diario.use_seed(cfg, LOG)
    assert len(pd.read_parquet(path)) == len(newer)


def test_download_is_skipped_if_already_done_today(cfg, monkeypatch):
    cfg["source"] = {"daily_ws_url": "https://example.invalid/ws", "daily_seed": "no-existe.parquet"}
    path = extract_diario.bronze_file(cfg)
    path.parent.mkdir(parents=True)
    raw_daily(pd.date_range("2026-01-03", periods=1, freq="7D")).to_parquet(path)
    monkeypatch.setattr(extract_diario.requests, "post", lambda *a, **k: pytest.fail("no debía llamar al servicio"))
    assert download_daily(cfg, LOG) is False


def test_pipeline_uses_the_daily_data(bronze):
    main.run(bronze, download=False)
    gold = pd.read_parquet(main.gold_path(bronze))
    assert daily_coverage(gold) >= 0.5
    from src.model.train import load_production
    assert "pais_cierre_vs_media" in load_production(bronze["paths"]["models"])[1]["features"]
