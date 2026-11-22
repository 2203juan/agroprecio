import importlib
import sys

import pytest
import yaml
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import main


@pytest.fixture
def client(bronze, tmp_path, monkeypatch):
    main.run(bronze, download=False)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(bronze, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("AGRO_CONFIG", str(path))
    # La API lee la configuración al importarse: se recarga con la de prueba
    sys.modules.pop("api.main", None)
    module = importlib.import_module("api.main")
    yield TestClient(module.app)
    REGISTRY.unregister(module.COLLECTOR)
    sys.modules.pop("api.main", None)


def test_health_and_alerts(client, bronze):
    assert client.get("/salud").json() == {"estado": "ok", "base_de_datos": True}
    assert {a["producto"] for a in client.get("/alertas").json()} == set(bronze["products"])


def test_history_of_unknown_product_is_404(client):
    assert client.get("/historico/Nada").status_code == 404
    assert len(client.get("/historico/Cilantro?semanas=5").json()) == 5


def test_list_is_saved_and_costed(client):
    body = {"restaurante": "Prueba", "items": [{"producto": "Cilantro", "kg_semana": 2},
                                              {"producto": "Inventado", "kg_semana": 3}]}
    saved = client.put("/lista", json=body).json()
    assert [i["producto"] for i in saved["items"]] == ["Cilantro"]
    assert saved["totales"]["costo_hoy"] > 0
    assert client.get("/lista").json()["restaurante"] == "Prueba"


def test_opinions_are_counted(client):
    assert client.get("/opiniones").json() == {"total": 0, "utiles": 0, "porcentaje_util": None}
    assert client.post("/opiniones", json={"util": True, "comentario": "compré antes"}).status_code == 201
    assert client.post("/opiniones", json={"util": False}).json() == {"total": 2, "utiles": 1, "porcentaje_util": 0.5}
    assert client.post("/opiniones", json={"util": True, "comentario": "x" * 301}).status_code == 422


def test_validity_and_metrics_table(client):
    assert client.get("/vigencia").json()["boletin_inicio"] == "2026-10-03"
    table = client.get("/metrics").json()["tabla"]
    assert {r["evaluado"] for r in table} == {"modelo", "baseline_persistencia", "baseline_estable", "baseline_comprar_todo"}
    assert "<table" in client.get("/metrics?formato=html").text


def test_monitoring_separates_real_predictions(client):
    state = client.get("/monitoreo").json()["estado"][0]
    assert state["predicciones_reales"] == 0 and state["accuracy_real"] is None


def test_prometheus_metrics(client):
    client.post("/opiniones", json={"util": True})
    text = client.get("/prometheus").text
    assert 'agroprecio_reglas_calidad{estado="ok"} 11.0' in text
    assert 'agroprecio_opiniones{respuesta="util"} 1.0' in text
    assert 'agroprecio_modelo_metrica{evaluado="modelo",metrica="f1_macro"}' in text
    assert "\nagroprecio_accuracy_real " not in text  # sin dato no se publica un cero falso


def test_prometheus_groups_by_route(client):
    client.get("/historico/Cilantro")
    text = client.get("/prometheus").text
    assert 'ruta="/historico/{producto}"' in text and "/historico/Cilantro" not in text
