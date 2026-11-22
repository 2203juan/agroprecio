"""Entrenamiento, evaluación contra baselines y registro de versiones del modelo."""
import json
from datetime import datetime
from pathlib import Path

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

from src.model.metrics import classification_metrics, simulated_saving
from src.transform.gold_transformations import BASE_FEATURES, FEATURES, classify

ALGORITHM = "Promedio de HistGradientBoosting y ExtraTrees"
BOOSTING = {"max_iter": 200, "learning_rate": 0.04, "max_leaf_nodes": 12, "min_samples_leaf": 40,
            "l2_regularization": 5, "early_stopping": False}
TREES = {"n_estimators": 400, "max_depth": 12, "min_samples_leaf": 10, "max_features": 0.4}


def preprocess(features):
    return ColumnTransformer([
        ("num", "passthrough", features),
        ("producto", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["producto"]),
    ], sparse_threshold=0)


def build_model(random_state, features=None):
    boosting = HistGradientBoostingClassifier(**BOOSTING, class_weight="balanced", random_state=random_state)
    trees = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        ExtraTreesClassifier(**TREES, class_weight="balanced", random_state=random_state, n_jobs=-1),
    )
    vote = VotingClassifier([("boosting", boosting), ("arboles", trees)], voting="soft")
    return Pipeline([("prep", preprocess(features or FEATURES)), ("clf", vote)])


def parameters(random_state):
    return {
        "algoritmo": ALGORITHM, "class_weight": "balanced", "random_state": random_state,
        **{f"boosting_{k}": v for k, v in BOOSTING.items()},
        **{f"arboles_{k}": v for k, v in TREES.items()},
    }


def evaluable(gold):
    """Filas con resultado conocido y con las variables básicas. Las demás variables
    pueden venir vacías: el modelo lo admite."""
    return gold.dropna(subset=BASE_FEATURES + ["clase"])


def split_by_time(gold, test_weeks):
    data = evaluable(gold)
    weeks = sorted(data["semana_inicio"].unique())
    cut = weeks[-test_weeks]
    return data[data["semana_inicio"] < cut], data[data["semana_inicio"] >= cut]


def training_rows(panel, before=None):
    """Todos los mercados de Cali con resultado conocido, antes de una fecha."""
    rows = panel.dropna(subset=["clase"])
    return rows if before is None else rows[rows["semana_inicio"] < before]


def usable_features(train_df):
    """Sin las variables que no tienen ningún dato (por ejemplo, el año anterior en un
    historial de menos de un año). Cada versión guarda las que usó."""
    return [f for f in FEATURES if train_df[f].notna().any()]


def evaluate(test, pred, proba=None):
    return {
        **classification_metrics(test["clase"], pred, proba),
        "ahorro_simulado": round(simulated_saving(test, pred), 4),
    }


def train(gold, panel, cfg, logger):
    """gold: Cavasa, para evaluar. panel: mercados de Cali, para entrenar."""
    mcfg = cfg["model"]
    _, test_df = split_by_time(gold, mcfg["test_weeks"])
    train_df = training_rows(panel, before=test_df["semana_inicio"].min())
    logger.info("Entrenamiento: %s filas de %s mercados, prueba: %s filas de %s",
                len(train_df), train_df["mercado"].nunique(), len(test_df), cfg["market"])

    features = usable_features(train_df)
    X = ["producto"] + features
    model = build_model(mcfg["random_state"], features)
    model.fit(train_df[X], train_df["clase"])
    proba = model.predict_proba(test_df[X])
    pred = model.classes_[proba.argmax(axis=1)]

    # Baseline de persistencia: lo que pasó la semana pasada vuelve a pasar
    baseline = test_df["cambio_1s"].apply(classify, threshold=mcfg["threshold"])

    metrics = {
        "modelo": evaluate(test_df, pred, proba),
        "baseline_persistencia": evaluate(test_df, baseline),
        "baseline_estable": evaluate(test_df, ["estable"] * len(test_df)),
        "baseline_comprar_todo": evaluate(test_df, ["sube"] * len(test_df)),
    }
    beats_baseline = metrics["modelo"]["f1_macro"] > metrics["baseline_persistencia"]["f1_macro"]
    good_enough = metrics["modelo"]["accuracy"] >= cfg["monitoring"]["min_accuracy"]

    version = datetime.now().strftime("v%Y%m%d_%H%M%S")
    models_dir = Path(cfg["paths"]["models"])
    models_dir.mkdir(exist_ok=True)

    # Dos archivos: el que se evaluó (no vio las semanas de prueba) y el que sale a producción,
    # con la misma receta y todos los datos. Las métricas son siempre del primero.
    final_df = training_rows(panel)
    final = build_model(mcfg["random_state"], features).fit(final_df[X], final_df["clase"])
    joblib.dump(model, models_dir / f"{version}_prueba.joblib", compress=3)
    joblib.dump(final, models_dir / f"{version}.joblib", compress=3)

    entry = {
        "version": version,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "estado": "produccion" if beats_baseline and good_enough else "rechazado",
        "datos": {
            "filas_entrenamiento": len(train_df),
            "filas_prueba": len(test_df),
            "filas_produccion": len(final_df),
            "mercados": sorted(train_df["mercado"].unique()),
            "desde": str(train_df["semana_inicio"].min().date()),
            "hasta": str(test_df["semana_inicio"].max().date()),
        },
        "features": features,
        "parametros": parameters(mcfg["random_state"]),
        "metricas": metrics,
    }
    register(entry, models_dir)
    logger.info("Modelo %s: %s | %s", version, entry["estado"], metrics["modelo"])

    test_out = test_df[["semana_inicio", "producto", "precio", "clase"]].copy()
    test_out["prediccion"] = pred
    return entry, test_out


def register(entry, models_dir):
    path = Path(models_dir) / "registry.json"
    registry = json.loads(path.read_text()) if path.exists() else []
    if entry["estado"] == "produccion":
        for old in registry:
            if old["estado"] == "produccion":
                old["estado"] = "archivado"
    registry.append(entry)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False, default=str))


def load_production(models_dir):
    path = Path(models_dir) / "registry.json"
    if not path.exists():
        return None, None
    registry = json.loads(path.read_text())
    prod = [r for r in registry if r["estado"] == "produccion"]
    if not prod:
        return None, None
    entry = prod[-1]
    return joblib.load(Path(models_dir) / f"{entry['version']}.joblib"), entry


def evaluated_model(models_dir, version):
    """El modelo con el que se midió una versión. Las anteriores a v0.6 solo tenían uno."""
    for name in (f"{version}_prueba.joblib", f"{version}.joblib"):
        path = Path(models_dir) / name
        if path.exists():
            return joblib.load(path)
    return None
