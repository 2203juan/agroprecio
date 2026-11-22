"""Qué tan vigente está la recomendación.

El DANE publica con rezago: puede pasar que la "próxima semana" de la que habla
la predicción ya haya pasado cuando el restaurante la lee.
"""
from datetime import date, timedelta

import pandas as pd


def freshness(week_start, today=None):
    """week_start: sábado en que empieza la semana del último boletín."""
    today = today or date.today()
    start = pd.Timestamp(week_start).date()
    target_start, target_end = start + timedelta(days=7), start + timedelta(days=13)
    return {
        "boletin_inicio": str(start),
        "boletin_fin": str(start + timedelta(days=6)),
        "recomendacion_inicio": str(target_start),
        "recomendacion_fin": str(target_end),
        "dias_desde_boletin": (today - (start + timedelta(days=6))).days,
        "vencida": today > target_end,
    }
