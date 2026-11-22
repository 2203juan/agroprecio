import pandas as pd

from src.load.load_database import read_table, save_table
from src.model.monitor import real_accuracy, score_predictions, weekly_accuracy
from src.model.predict import add_backtest

WEEK = pd.Timestamp("2026-10-03")


def log_row(product, prediction, confidence, week=WEEK):
    return {"semana_inicio": week, "producto": product, "precio": 1000.0, "prediccion": prediction,
            "confianza": confidence, "modelo_version": "v1", "fecha_prediccion": "2026-10-03"}


def scored(rows):
    gold = pd.DataFrame([{"semana_inicio": WEEK, "producto": p, "clase": "sube"} for p in ["A", "B", "C"]])
    return score_predictions(pd.DataFrame(rows), gold)


def test_backtest_does_not_count_as_real():
    s = scored([log_row("A", "sube", None), log_row("B", "baja", 0.6), log_row("C", "sube", 0.5)])
    assert real_accuracy(s) == (2, 0.5)
    assert weekly_accuracy(s)["reales"].tolist() == [2]


def test_no_real_predictions_yet():
    assert real_accuracy(scored([log_row("A", "sube", None)])) == (0, None)


def test_retraining_keeps_real_predictions():
    log = pd.DataFrame([log_row("A", "sube", 0.7)])
    backtest = pd.DataFrame([log_row("A", "baja", None), log_row("B", "baja", None)])
    out = add_backtest(log, backtest).set_index("producto")
    assert out.loc["A", "prediccion"] == "sube" and out.loc["A", "confianza"] == 0.7
    assert len(out) == 2


def test_history_table_accepts_new_columns(tmp_path):
    db = tmp_path / "x.db"
    save_table(pd.DataFrame([{"fecha": "1", "accuracy": 0.5}]), "monitoreo", db, mode="append")
    save_table(pd.DataFrame([{"fecha": "2", "accuracy": 0.4, "predicciones_reales": 20}]), "monitoreo", db, mode="append")
    df = read_table("monitoreo", db)
    assert len(df) == 2 and df["predicciones_reales"].iloc[-1] == 20
