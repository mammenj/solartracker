"""Async SQLite storage for meter readings.

A :class:`MeterReadingStore` owns a single long-lived ``aiosqlite`` connection
for its database file.  One store is created per request (and attached to
``request.store``), so every query made while handling that request reuses the
same connection instead of opening a new one - and a new worker thread - each
time.

Because the connection is shared, a :class:`asyncio.Lock` serialises
read-modify-write sequences (``save_or_update``), so two concurrent requests
handling the *same* store cannot interleave and see each other's uncommitted
work.  The connection is opened lazily on first use and is bound to the event
loop that opened it.

Schema creation is also memoised process-wide (:data:`_schema_ready`): a store
is created per request, so without it the ``CREATE TABLE``/``CREATE INDEX``
statements would re-run on the first query of every request.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

#: Resolved db paths whose schema has already been created this process.
_schema_ready: set[Path] = set()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meter_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    import REAL NOT NULL,
    export REAL NOT NULL,
    solar_gen REAL NOT NULL,
    addedon TEXT NOT NULL
)
"""


def _make_reading(row) -> object:
    """Build a lightweight MeterReading-like object from a DB row."""
    return type('Reading', (), {
        'id': row["id"],
        'date': datetime.strptime(row["date"], "%Y-%m-%d"),
        'import_units': row["import"],
        'export_units': row["export"],
        'solar_units': row["solar_gen"],
    })()


class MeterReadingStore:
    """Abstracts SQLite storage for meter readings."""

    def __init__(self, db_filepath: Path):
        """
        Initialise the store.

        The underlying connection is opened lazily on first use, so no I/O
        happens here (which also keeps construction safe outside a running
        event loop).

        Args:
            db_filepath: Path to the SQLite database file.
        """
        self.db_filepath = Path(db_filepath)
        self._conn: Optional[aiosqlite.Connection] = None
        self._schema_initialized = False
        # Serialises read-modify-write sequences on the shared connection.
        self._write_lock = asyncio.Lock()

    # Whitelist of UI sort keys -> SQL columns (prevents SQL injection in ORDER BY)
    SORT_COLUMNS = {
        "date": "date",
        "solar": "solar_gen",
        "export": "export",
        "import": "import",
    }

    async def _connect(self) -> aiosqlite.Connection:
        """Return the store's connection, opening it on first use."""
        if self._conn is None:
            Path(self.db_filepath).parent.mkdir(parents=True, exist_ok=True)
            conn = await aiosqlite.connect(self.db_filepath)
            conn.row_factory = aiosqlite.Row
            self._conn = conn
        return self._conn

    async def aclose(self) -> None:
        """Close the underlying connection, if one is open."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self._schema_initialized = False

    async def _init_schema(self) -> None:
        """Create the readings table if it doesn't exist.

        Skipped entirely once this process has created the schema for the
        path, so the (idempotent but non-free) DDL does not re-run on the first
        query of every request.
        """
        key = self.db_filepath.resolve()
        if key in _schema_ready:
            return
        conn = await self._connect()
        await conn.execute(_SCHEMA_SQL)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON meter_records(date)")
        await conn.commit()
        _schema_ready.add(key)

    async def _ensure_schema(self) -> None:
        """Ensure schema is initialized (lazy initialization)."""
        if not self._schema_initialized:
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

        conn = await self._connect()
        total_row = await conn.execute("SELECT COUNT(*) FROM meter_records")
        total = (await total_row.fetchone())[0]
        cursor = await conn.execute(
            "SELECT id, date, import, export, solar_gen FROM meter_records "
            "ORDER BY %s %s, date ASC LIMIT ? OFFSET ?" % (sort_col, sort_dir),
            (page_size, offset),
        )
        rows = await cursor.fetchall()

        return [_make_reading(r) for r in rows], total

    async def load_all(self) -> list:
        """
        Load all meter readings from the database, sorted by date.

        Returns:
            List of MeterReading objects sorted by date.
        """
        await self._ensure_schema()
        conn = await self._connect()
        cursor = await conn.execute(
            "SELECT id, date, import, export, solar_gen FROM meter_records ORDER BY date ASC"
        )
        rows = await cursor.fetchall()
        return [_make_reading(r) for r in rows]

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

        conn = await self._connect()
        async with self._write_lock:
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
        conn = await self._connect()
        async with self._write_lock:
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
        conn = await self._connect()
        cursor = await conn.execute(
            "SELECT id, date, import, export, solar_gen FROM meter_records WHERE date = ?",
            (date_str,),
        )
        row = await cursor.fetchone()
        return _make_reading(row) if row else None

    async def count(self) -> int:
        """Get the total number of readings in the database."""
        await self._ensure_schema()
        conn = await self._connect()
        cursor = await conn.execute("SELECT COUNT(*) FROM meter_records")
        row = await cursor.fetchone()
        return row[0]

    async def clear_all(self) -> None:
        """Delete all readings from the database."""
        await self._ensure_schema()
        conn = await self._connect()
        async with self._write_lock:
            await conn.execute("DELETE FROM meter_records")
            await conn.commit()
