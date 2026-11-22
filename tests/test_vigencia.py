from datetime import date

import pytest

from src.vigencia import freshness


@pytest.mark.parametrize("today, expired", [
    (date(2026, 11, 7), False), (date(2026, 11, 13), False), (date(2026, 11, 14), True),
])
def test_recommendation_expires_after_its_week(today, expired):
    assert freshness("2026-10-31 00:00:00", today)["vencida"] is expired


def test_dates():
    f = freshness("2026-10-31", date(2026, 11, 22))
    assert (f["recomendacion_inicio"], f["recomendacion_fin"]) == ("2026-11-07", "2026-11-13")
    assert f["dias_desde_boletin"] == 16
