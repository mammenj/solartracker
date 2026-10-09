import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from libsolar import MeterReading


class MeterReadingStore:
    """Abstracts SQLite storage for meter readings."""

    def __init__(self, db_filepath: Path):
        """
        Initialize the store and create the schema if needed.

        Args:
            db_filepath: Path to the SQLite database file.
        """
        self.db_filepath = db_filepath
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the readings table if it doesn't exist."""
        with sqlite3.connect(self.db_filepath) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meter_reacords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    import REAL NOT NULL,
                    export REAL NOT NULL,
                    solar_gen REAL NOT NULL,
                    addedon TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON meter_records(date)")
            conn.commit()

    def load_all(self) -> list[MeterReading]:
        """
        Load all meter readings from the database, sorted by date.

        Returns:
            List of MeterReading objects sorted by date.
        """
        readings = []
        with sqlite3.connect(self.db_filepath) as conn:
            cursor = conn.execute(
                "SELECT date, import, export, solar_gen FROM meter_records ORDER BY date ASC"
            )
            for row in cursor.fetchall():
                date_str, import_units, export_units, solar_units = row
                date = datetime.strptime(date_str, "%Y-%m-%d")
                readings.append(
                    MeterReading(date, import_units, export_units, solar_units)
                )
        return readings

    def save_or_update(self, reading: MeterReading) -> bool:
        """
        Save a new reading or update an existing one.

        Args:
            reading: The MeterReading to save or update.

        Returns:
            True if this was an update, False if it was a new insert.
        """
        date_str = reading.date.strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        with sqlite3.connect(self.db_filepath) as conn:
            # Check if reading exists for this date
            cursor = conn.execute(
                "SELECT id FROM meter_records WHERE date = ?", (date_str,)
            )
            existing = cursor.fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE meter_records
                    SET import = ?, export = ?, solar_gen = ?, addedon = ?
                    WHERE date = ?
                    """,
                    (
                        reading.import_units,
                        reading.export_units,
                        reading.solar_units,
                        now_str,
                    ),
                )
                conn.commit()
                return True
            else:
                conn.execute(
                    """
                    INSERT INTO meter_records (date, import, export, solar_gen, addedon)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        date_str,
                        reading.import_units,
                        reading.export_units,
                        reading.solar_units,
                        now_str,
                    ),
                )
                conn.commit()
                return False

    def delete(self, date: datetime) -> bool:
        """
        Delete a reading by date.

        Args:
            date: The date of the reading to delete.

        Returns:
            True if a reading was deleted, False if no reading existed for that date.
        """
        date_str = date.strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_filepath) as conn:
            cursor = conn.execute(
                "DELETE FROM meter_readings WHERE date = ?", (date_str,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_by_date(self, date: datetime) -> Optional[MeterReading]:
        """
        Retrieve a specific reading by date.

        Args:
            date: The date to look up.

        Returns:
            MeterReading if found, None otherwise.
        """
        date_str = date.strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_filepath) as conn:
            cursor = conn.execute(
                "SELECT date, import_units, export_units, solar_units FROM meter_readings WHERE date = ?",
                (date_str,),
            )
            row = cursor.fetchone()
            if row:
                date_obj, import_units, export_units, solar_units = row
                return MeterReading(date_obj, import_units, export_units, solar_units)
        return None

    def count(self) -> int:
        """Get the total number of readings in the database."""
        with sqlite3.connect(self.db_filepath) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM meter_readings")
            return cursor.fetchone()[0]

    def clear_all(self) -> None:
        """Delete all readings from the database."""
        with sqlite3.connect(self.db_filepath) as conn:
            conn.execute("DELETE FROM meter_readings")
            conn.commit()
