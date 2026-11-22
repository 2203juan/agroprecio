import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.llm.boletin import generate_bulletin, numbers_are_grounded, template_bulletin

LOG = logging.getLogger("test")


@pytest.fixture
def alerts():
    return pd.DataFrame([
        {"semana_inicio": "2026-10-31", "producto": "Tomate chonto", "precio": 3738.0, "cambio_1s": 0.17, "prediccion": "sube", "confianza": 0.5},
        {"semana_inicio": "2026-10-31", "producto": "Cilantro", "precio": 3854.0, "cambio_1s": -0.06, "prediccion": "baja", "confianza": 0.4},
    ])


@pytest.fixture
def claude(monkeypatch, cfg):
    """Reemplaza el SDK de Anthropic por una respuesta fija."""
    Path(cfg["paths"]["logs"]).mkdir()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")

    def answer(text=None, stop_reason="end_turn", error=None):
        def create(**_):
            if error:
                raise RuntimeError(error)
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=10, output_tokens=5), stop_reason=stop_reason,
                                   content=[SimpleNamespace(type="text", text=text)])
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda: client))
    return answer


def last_record(cfg):
    return json.loads((Path(cfg["paths"]["logs"]) / "llm.jsonl").read_text().splitlines()[-1])


def test_guardrail_accepts_real_prices_and_rejects_invented_ones(alerts):
    assert numbers_are_grounded("El tomate está a $3.738 y el cilantro a 3854.", alerts)
    assert not numbers_are_grounded("El tomate está a $9.999.", alerts)


def test_template_separates_buy_and_wait(alerts):
    text = template_bulletin(alerts)
    assert "comprar ya: Tomate chonto" in text and "esperar con: Cilantro" in text


def test_good_answer_is_published(alerts, cfg, claude):
    claude("Compra ya el tomate, que está a $3.738.")
    out = generate_bulletin(alerts, cfg, LOG)
    assert out["fuente"] == "claude" and "3.738" in out["texto"]
    assert last_record(cfg)["tokens_entrada"] == 10


def test_invented_price_is_discarded(alerts, cfg, claude):
    claude("El tomate va a costar $9.999.")
    assert generate_bulletin(alerts, cfg, LOG)["fuente"] == "plantilla"
    assert "descartado" in last_record(cfg)


def test_truncated_answer_uses_template(alerts, cfg, claude):
    claude("Compra ya el", stop_reason="max_tokens")
    assert generate_bulletin(alerts, cfg, LOG)["fuente"] == "plantilla"


def test_error_uses_template(alerts, cfg, claude):
    claude(error="sin conexión")
    assert generate_bulletin(alerts, cfg, LOG)["fuente"] == "plantilla"
    assert last_record(cfg)["error"] == "sin conexión"


def test_without_key_uses_template(alerts, cfg):
    Path(cfg["paths"]["logs"]).mkdir()
    assert generate_bulletin(alerts, cfg, LOG)["fuente"] == "plantilla"
