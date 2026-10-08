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
        date: datetime,
        import_units: float,
        export_units: float,
        solar_units: float,
    ):
        self.date = date
        self.import_units = import_units
        self.export_units = export_units
        self.solar_units = solar_units

    @classmethod
    def from_file_line(cls, line: str) -> MeterReading | None:
        parts = line.strip().split("|")
        if len(parts) < 4:
            return None
        try:
            date = datetime.strptime(parts[0], "%Y-%m-%d")
            imp = float(parts[1])
            exp = float(parts[2])
            solar = float(parts[3])
            return cls(date, imp, exp, solar)
        except ValueError:
            return None

    def to_file_line(self) -> str:
        return f"{self.date.strftime('%Y-%m-%d')}|{self.import_units:.2f}|{self.export_units:.2f}|{self.solar_units:.2f}\n"


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


class SolarTracker:
    """Manages reading history state, validation, and calculations."""

    def __init__(self, data_filepath: Path):
        self.filepath = data_filepath
        self.history: list[MeterReading] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        self.history.clear()
        if not self.filepath.exists():
            return
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                reading = MeterReading.from_file_line(line)
                if reading:
                    self.history.append(reading)
        self.history.sort(key=lambda r: r.date)

    def _save_all_to_file(self) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(reading.to_file_line() for reading in self.history)

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

    def save_or_update_reading(
        self, reading: MeterReading
    ) -> tuple[bool, ReadingPeriod | None]:
        existing_index = next(
            (
                i
                for i, r in enumerate(self.history)
                if r.date.date() == reading.date.date()
            ),
            None,
        )
        is_update = existing_index is not None

        if is_update:
            self.history[existing_index] = reading
        else:
            self.history.append(reading)

        self.history.sort(key=lambda r: r.date)
        self._save_all_to_file()

        idx = self.history.index(reading)
        period = ReadingPeriod(self.history[idx - 1], reading) if idx > 0 else None
        return is_update, period

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
