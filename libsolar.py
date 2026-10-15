from datetime import datetime
from pathlib import Path
from typing import TypedDict


class TotalsDict(TypedDict):
    total_days: int
    total_import: float
    total_export: float
    total_solar: float
    total_balance: float
    total_consumption: float


class MeterReading:
    """Represents a single mandatory cumulative meter reading snapshot."""

    def __init__(
        self,
        id: int,
        date: datetime,
        import_units: float,
        export_units: float,
        solar_units: float,
    ):
        self.id = id
        self.date = date
        self.import_units = import_units
        self.export_units = export_units
        self.solar_units = solar_units


class ReadingPeriod:
    """Calculates deltas and metrics between two consecutive snapshots."""

    def __init__(self, start_reading: MeterReading, end_reading: MeterReading):
        self.start = start_reading
        self.end = end_reading

    @property
    def days(self) -> int:
        return (self.end.date - self.start.date).days

    @property
    def import_diff(self) -> float:
        return self.end.import_units - self.start.import_units

    @property
    def export_diff(self) -> float:
        return self.end.export_units - self.start.export_units

    @property
    def net_balance(self) -> float:
        return self.export_diff - self.import_diff

    @property
    def solar_yield(self) -> float:
        return self.end.solar_units - self.start.solar_units

    @property
    def consumption(self) -> float:
        return (self.solar_yield + self.import_diff) - self.export_diff

    @property
    def avg_daily_consumption(self) -> float:
        return self.consumption / self.days if self.days > 0 else self.consumption


class EnergyExtrapolator:
    """Extrapolates period data to weekly (7-day) normalized values."""

    def __init__(self, reading_period: ReadingPeriod):
        self.period = reading_period
        self.days = reading_period.days

    @property
    def weekly_import(self) -> float:
        """Normalize import to 7-day equivalent."""
        if self.days <= 0:
            return 0.0
        weekly_import = round((self.period.import_diff / self.days) * 7, 2)
        # print("weekly imprt -----", weekly_import)
        return weekly_import

    @property
    def weekly_export(self) -> float:
        """Normalize export to 7-day equivalent."""
        if self.days <= 0:
            return 0.0
        return round((self.period.export_diff / self.days) * 7, 2)

    @property
    def weekly_solar_yield(self) -> float:
        """Normalize solar yield to 7-day equivalent."""
        if self.days <= 0:
            return 0.0
        return round((self.period.solar_yield / self.days) * 7, 2)

    @property
    def weekly_consumption(self) -> float:
        """Normalize consumption to 7-day equivalent."""
        if self.days <= 0:
            return 0.0
        return round((self.period.consumption / self.days) * 7, 2)

    @property
    def weekly_net_balance(self) -> float:
        """Normalize net balance to 7-day equivalent."""
        if self.days <= 0:
            return 0.0
        return round((self.period.net_balance / self.days) * 7, 2)


class SolarTracker:
    """Manages reading history state, validation, and calculations."""

    def __init__(self, data_filepath: Path):
        self.filepath = data_filepath
        self.history: list[MeterReading] = []

    def validate_reading(self, new_reading: MeterReading) -> tuple[bool, str]:
        prior_readings = [r for r in self.history if r.date < new_reading.date]
        if not prior_readings:
            return True, ""

        last = prior_readings[-1]
        if new_reading.import_units < last.import_units:
            return (
                False,
                f"Import reading ({new_reading.import_units:.2f} kWh) cannot be lower than prior reading ({last.import_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )
        if new_reading.export_units < last.export_units:
            return (
                False,
                f"Export reading ({new_reading.export_units:.2f} kWh) cannot be lower than prior reading ({last.export_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )
        if new_reading.solar_units < last.solar_units:
            return (
                False,
                f"Solar reading ({new_reading.solar_units:.2f} kWh) cannot be lower than prior reading ({last.solar_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )

        return True, ""

    def get_periods(self) -> list[ReadingPeriod]:
        return [
            ReadingPeriod(self.history[i - 1], self.history[i])
            for i in range(1, len(self.history))
        ]

    def get_totals(self) -> TotalsDict:
        periods = self.get_periods()

        return {
            "total_days": sum(p.days for p in periods),
            "total_import": sum(p.import_diff for p in periods),
            "total_export": sum(p.export_diff for p in periods),
            "total_solar": sum(p.solar_yield for p in periods),
            "total_balance": sum(p.net_balance for p in periods),
            "total_consumption": sum(p.consumption for p in periods),
        }
