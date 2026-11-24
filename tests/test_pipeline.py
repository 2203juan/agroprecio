import pandas as pd
import pytest

import main
from src.load.load_database import read_table
from src.model.train import load_production


def test_full_pipeline_publishes_everything(bronze):
    main.run(bronze, download=False)
    db = bronze["paths"]["database"]
    assert set(read_table("alertas", db)["producto"]) == set(bronze["products"])
    assert read_table("calidad_datos", db)["ok"].all()
    assert read_table("boletines", db)["fuente"].tolist() == ["plantilla"]
    assert load_production(bronze["paths"]["models"])[1]["estado"] == "produccion"


def test_stages_one_by_one_give_the_same_result(bronze, tmp_path):
    log = main.get_logger(bronze["paths"]["logs"])
    for name in ["silver", "gold", "calidad", "modelo", "prediccion", "boletin"]:
        main.STAGES[name](bronze, log)
    by_stage = read_table("alertas", bronze["paths"]["database"]).drop(columns=["modelo_version", "fecha_prediccion"])

    other = {**bronze, "paths": {**bronze["paths"], "models": str(tmp_path / "models2"),
                                 "database": str(tmp_path / "otra.db")}}
    main.run(other, download=False)
    together = read_table("alertas", other["paths"]["database"]).drop(columns=["modelo_version", "fecha_prediccion"])
    pd.testing.assert_frame_equal(by_stage, together)


def test_quality_rules_of_a_run_share_the_date(bronze):
    main.run(bronze, download=False)
    quality = read_table("calidad_datos", bronze["paths"]["database"])
    assert quality["fecha"].nunique() == 1 and len(quality) == 12


def test_critical_quality_failure_stops_before_publishing(bronze, monkeypatch):
    log = main.get_logger(bronze["paths"]["logs"])
    main.stage_silver(bronze, log)
    main.stage_gold(bronze, log)
    silver = pd.read_parquet(main.silver_path(bronze))
    silver.loc[0, "precio_medio"] = -5
    silver.to_parquet(main.silver_path(bronze), index=False)
    with pytest.raises(SystemExit):
        main.stage_calidad(bronze, log)
    assert read_table("features", bronze["paths"]["database"]).empty


def test_prediction_without_model_stops(bronze):
    log = main.get_logger(bronze["paths"]["logs"])
    for name in ["silver", "gold", "calidad"]:
        main.STAGES[name](bronze, log)
    with pytest.raises(SystemExit):
        main.stage_prediccion(bronze, log)


def test_running_twice_does_not_duplicate_predictions(bronze):
    main.run(bronze, download=False)
    main.run(bronze, download=False)
    pred = read_table("predicciones", bronze["paths"]["database"])
    assert not pred.duplicated(["semana_inicio", "producto"]).any()
