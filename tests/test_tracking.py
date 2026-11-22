import logging

import pytest

import main
from src.model import tracking

LOG = logging.getLogger("test")


def test_without_server_nothing_is_logged(cfg):
    assert tracking.sync_registry(cfg, LOG) == 0
    with tracking.llm_span("x", LOG) as span:
        span.set_inputs({"a": 1})


def test_unreachable_server_does_not_stop_the_pipeline(bronze, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:9")
    main.run(bronze, download=False)


def test_errors_inside_the_span_are_not_hidden():
    with pytest.raises(ValueError):
        with tracking.llm_span("x", LOG):
            raise ValueError("error del boletín")


def test_only_numbers_become_metrics():
    entry = {"metricas": {"modelo": {"f1_macro": 0.44, "log_loss": None}, "baseline_estable": {"f1_macro": 0.14}}}
    assert tracking.flat_metrics(entry) == {"modelo_f1_macro": 0.44, "baseline_estable_f1_macro": 0.14}
