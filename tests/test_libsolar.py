"""Unit tests for the pure calculation models (libsolar.py)."""

from datetime import datetime

import pytest

from libsolar import EnergyExtrapolator, MeterReading, ReadingPeriod


def reading(day: int, import_units: float, export_units: float, solar_units: float) -> MeterReading:
    return MeterReading(0, datetime(2026, 1, day), import_units, export_units, solar_units)


def test_period_metrics():
    period = ReadingPeriod(reading(1, 100, 200, 300), reading(8, 170, 240, 450))

    assert period.days == 7
    assert period.import_diff == 70
    assert period.export_diff == 40
    assert period.net_balance == -30  # export_diff - import_diff
    assert period.solar_yield == 150
    assert period.consumption == 180  # solar + import - export
    assert period.avg_daily_consumption == pytest.approx(180 / 7)


def test_avg_daily_consumption_handles_zero_days():
    period = ReadingPeriod(reading(1, 1, 1, 1), reading(1, 5, 5, 5))
    assert period.days == 0
    assert period.avg_daily_consumption == period.consumption


def test_energy_extrapolator_normalises_to_weekly():
    period = ReadingPeriod(reading(1, 0, 0, 0), reading(8, 70, 35, 140))
    extrapolator = EnergyExtrapolator(period)

    assert extrapolator.weekly_import == 70
    assert extrapolator.weekly_export == 35
    assert extrapolator.weekly_solar_yield == 140
    assert extrapolator.weekly_consumption == 175  # (140 + 70 - 35)
    assert extrapolator.weekly_net_balance == -35  # (35 - 70)


@pytest.mark.parametrize(
    "prop",
    [
        "weekly_import",
        "weekly_export",
        "weekly_solar_yield",
        "weekly_consumption",
        "weekly_net_balance",
    ],
)
def test_energy_extrapolator_returns_zero_for_zero_day_period(prop):
    period = ReadingPeriod(reading(1, 1, 1, 1), reading(1, 5, 5, 5))
    assert getattr(EnergyExtrapolator(period), prop) == 0.0
