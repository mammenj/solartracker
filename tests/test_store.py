"""Unit tests for the SQLite reading store (libsolar_sqlite.py)."""

from datetime import datetime

import pytest

from libsolar import MeterReading
from libsolar_sqlite import MeterReadingStore


def reading(day: int, import_units: float, export_units: float, solar_units: float) -> MeterReading:
    return MeterReading(0, datetime(2026, 1, day), import_units, export_units, solar_units)


@pytest.fixture
def store(tmp_path) -> MeterReadingStore:
    return MeterReadingStore(tmp_path / "store.db")


async def test_save_new_reading_returns_false_and_persists(store):
    assert await store.save_or_update(reading(1, 10, 20, 30)) is False

    readings, total = await store.load_page()
    assert total == 1
    assert readings[0].date == datetime(2026, 1, 1)
    assert readings[0].import_units == 10
    assert readings[0].export_units == 20
    assert readings[0].solar_units == 30


async def test_save_same_date_updates_in_place(store):
    await store.save_or_update(reading(1, 10, 20, 30))
    assert await store.save_or_update(reading(1, 11, 21, 31)) is True

    readings, total = await store.load_page()
    assert total == 1
    assert readings[0].import_units == 11
    assert readings[0].export_units == 21
    assert readings[0].solar_units == 31


async def test_load_page_sorts_by_date(store):
    for day in (1, 2, 3):
        await store.save_or_update(reading(day, day * 10, day * 20, day * 30))

    ascending, _ = await store.load_page(sort_by="date", order="asc")
    assert [r.date.day for r in ascending] == [1, 2, 3]

    descending, _ = await store.load_page(sort_by="date", order="desc")
    assert [r.date.day for r in descending] == [3, 2, 1]


async def test_load_page_pages_by_numeric_column(store):
    for day in (1, 2, 3):
        await store.save_or_update(reading(day, day * 10, day * 20, day * 30))

    page1, total = await store.load_page(sort_by="import", order="asc", page=1, page_size=2)
    assert total == 3
    assert [r.import_units for r in page1] == [10, 20]

    page2, _ = await store.load_page(sort_by="import", order="asc", page=2, page_size=2)
    assert [r.import_units for r in page2] == [30]


async def test_load_page_falls_back_to_date_for_unknown_sort_key(store):
    await store.save_or_update(reading(1, 1, 1, 1))
    readings, total = await store.load_page(sort_by="; DROP TABLE meter_records--", order="desc")
    assert total == 1
    assert len(readings) == 1


async def test_load_all_returns_readings_in_date_order(store):
    for day in (3, 1, 2):
        await store.save_or_update(reading(day, day, day, day))
    assert [r.date.day for r in await store.load_all()] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Lookup / delete / reset helpers
# ---------------------------------------------------------------------------
async def test_delete_removes_reading(store):
    await store.save_or_update(reading(1, 1, 1, 1))
    assert await store.delete(datetime(2026, 1, 1)) is True
    assert await store.load_all() == []
    assert await store.delete(datetime(2026, 1, 1)) is False


async def test_get_by_date_returns_reading(store):
    await store.save_or_update(reading(1, 1, 2, 3))

    found = await store.get_by_date(datetime(2026, 1, 1))
    assert found is not None
    assert found.date == datetime(2026, 1, 1)
    assert found.import_units == 1
    assert found.export_units == 2
    assert found.solar_units == 3

    assert await store.get_by_date(datetime(2026, 1, 2)) is None


async def test_count(store):
    assert await store.count() == 0
    await store.save_or_update(reading(1, 1, 2, 3))
    assert await store.count() == 1


async def test_clear_all(store):
    await store.save_or_update(reading(1, 1, 2, 3))
    await store.clear_all()
    assert await store.load_all() == []
    assert await store.count() == 0
