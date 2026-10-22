"""Async SQLite storage for meter readings."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional


class MeterReadingStore:
    """Abstracts SQLite storage for meter readings (async version)."""

    def __init__(self, db_filepath: Path):
        """
        Initialize the store and create the schema if needed.

        Args:
            db_filepath: Path to the SQLite database file.
        """

        self.db_filepath = db_filepath
        # Schema initialization is lazy - happens on first use

    # Whitelist of UI sort keys -> SQL columns (prevents SQL injection in ORDER BY)
    SORT_COLUMNS = {
        "date": "date",
        "solar": "solar_gen",
        "export": "export",
        "import": "import",
    }

    async def _init_schema(self) -> None:
        """Create the readings table if it doesn't exist."""
        async with aiosqlite.connect(self.db_filepath) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meter_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    import REAL NOT NULL,
                    export REAL NOT NULL,
                    solar_gen REAL NOT NULL,
                    addedon TEXT NOT NULL
                )
                """
            )
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON meter_records(date)")
            await conn.commit()

    async def _ensure_schema(self) -> None:
        """Ensure schema is initialized (lazy initialization)."""
        if not hasattr(self, '_schema_initialized'):
            await self._init_schema()
            self._schema_initialized = True

    async def load_page(
        self,
        sort_by: str = "date",
        order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        """
        Load one page of meter readings, sorted server-side.

        Args:
            sort_by: UI sort key (must be one of SORT_COLUMNS).
            order: "asc" or "desc".
            page: 1-based page number.
            page_size: Number of rows per page.

        Returns:
            Tuple of (readings on this page, total number of records).
        """
        await self._ensure_schema()
        sort_col = self.SORT_COLUMNS.get(sort_by, "date")
        sort_dir = "DESC" if order == "desc" else "ASC"
        page = max(1, int(page))
        page_size = max(1, int(page_size))
        offset = (page - 1) * page_size

        async with aiosqlite.connect(self.db_filepath) as conn:
            total_row = await conn.execute("SELECT COUNT(*) FROM meter_records")
            total = (await total_row.fetchone())[0]
            cursor = await conn.execute(
                "SELECT id, date, import, export, solar_gen FROM meter_records "
                "ORDER BY %s %s, date ASC LIMIT ? OFFSET ?" % (sort_col, sort_dir),
                (page_size, offset),
            )
            rows = await cursor.fetchall()

        readings = []
        for id, date_str, import_units, export_units, solar_units in rows:
            # Create a simple object that mimics MeterReading
            readings.append(
                type('Reading', (), {
                    'id': id,
                    'date': datetime.strptime(date_str, "%Y-%m-%d"),
                    'import_units': import_units,
                    'export_units': export_units,
                    'solar_units': solar_units,
                })()
            )
        return readings, total

    async def load_all(self) -> list:
        """
        Load all meter readings from the database, sorted by date.

        Returns:
            List of MeterReading objects sorted by date.
        """
        await self._ensure_schema()
        readings = []
        async with aiosqlite.connect(self.db_filepath) as conn:
            cursor = await conn.execute(
                "SELECT id, date, import, export, solar_gen FROM meter_records ORDER BY date ASC"
            )
            for row in await cursor.fetchall():
                id, date_str, import_units, export_units, solar_units = row
                readings.append(
                    type('Reading', (), {
                        'id': id,
                        'date': datetime.strptime(date_str, "%Y-%m-%d"),
                        'import_units': import_units,
                        'export_units': export_units,
                        'solar_units': solar_units,
                    })()
                )
        return readings

    async def save_or_update(self, reading) -> bool:
        """
        Save a new reading or update an existing one.

        Args:
            reading: The MeterReading to save or update.

        Returns:
            True if this was an update, False if it was a new insert.
        """
        await self._ensure_schema()
        date_str = reading.date.strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        async with aiosqlite.connect(self.db_filepath) as conn:
            # Check if reading exists for this date
            cursor = await conn.execute(
                "SELECT id FROM meter_records WHERE date = ?", (date_str,)
            )
            existing = await cursor.fetchone()

            if existing:
                await conn.execute(
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
                        date_str,
                    ),
                )
                await conn.commit()
                return True
            else:
                await conn.execute(
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
                await conn.commit()
                return False

    async def delete(self, date: datetime) -> bool:
        """
        Delete a reading by date.

        Args:
            date: The date of the reading to delete.

        Returns:
            True if a reading was deleted, False if no reading existed for that date.
        """
        await self._ensure_schema()
        date_str = date.strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_filepath) as conn:
            cursor = await conn.execute(
                "DELETE FROM meter_records WHERE date = ?", (date_str,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def get_by_date(self, date: datetime) -> Optional[object]:
        """
        Retrieve a specific reading by date.

        Args:
            date: The date to look up.

        Returns:
            Reading object if found, None otherwise.
        """
        await self._ensure_schema()
        date_str = date.strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_filepath) as conn:
            cursor = await conn.execute(
                "SELECT id, date, import, export, solar_gen FROM meter_records WHERE date = ?",
                (date_str,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        id, date_value, import_units, export_units, solar_units = row
        return type('Reading', (), {
            'id': id,
            'date': datetime.strptime(date_value, "%Y-%m-%d"),
            'import_units': import_units,
            'export_units': export_units,
            'solar_units': solar_units,
        })()

    async def count(self) -> int:
        """Get the total number of readings in the database."""
        await self._ensure_schema()
        async with aiosqlite.connect(self.db_filepath) as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM meter_records")
            row = await cursor.fetchone()
            return row[0]

    async def clear_all(self) -> None:
        """Delete all readings from the database."""
        await self._ensure_schema()
        async with aiosqlite.connect(self.db_filepath) as conn:
            await conn.execute("DELETE FROM meter_records")
            await conn.commit()