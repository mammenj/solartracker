"""Entry service functions for reading management."""

from math import ceil
from bottle import request
from auth.deps import get_user_store
from libsolar import MeterReading, ReadingPeriod, TotalsDict
from config import load_config

config = load_config()


def get_display_params() -> dict:
    """
    Parse paging/sorting query params for the readings list and fetch the page
    from the store (all paging/sorting happens server-side, in Python/SQL).

    Returns dict with: readings, total, page, page_size, total_pages,
    sort, order, headers.
    """
    from math import ceil
    from libsolar_sqlite import MeterReadingStore

    try:
        page = max(1, int(request.params.get("page", "1")))
    except (ValueError, TypeError):
        page = 1

    sort = request.params.get("sort", "date")
    order = request.params.get("order", "desc")
    sort = sort if sort in MeterReadingStore.SORT_COLUMNS else "date"
    order = order if order in ("asc", "desc") else "desc"

    page_size = 10
    readings, total = get_user_store().load_page(sort, order, page, page_size)
    total_pages = max(1, ceil(total / page_size)) if total else 1

    return {
        "readings": readings,
        "total": total,
        "page": min(page, total_pages),
        "page_size": page_size,
        "total_pages": total_pages,
        "sort": sort,
        "order": order,
        "headers": sortable_headers(
            sort,
            order,
            [
                ("date", "Date"),
                ("solar", "Solar Gen"),
                ("export", "Export"),
                ("import", "Import"),
            ],
        ),
    }


def validate_reading(new_reading) -> tuple[bool, str]:
    """Validate a new reading against the last stored reading."""
    readings = get_user_store().load_all()
    if not readings:
        return True, ""

    last = readings[-1]
    is_present = any(r.date == new_reading.date for r in readings)
    if is_present:
        return True, "Updating"
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


def sortable_headers(sort: str, order: str, fields: list[tuple[str, str]]) -> list[dict]:
    """
    Build sortable column-header metadata for htmx-clickable <th> elements.
    """
    headers = []
    for key, label in fields:
        active = key == sort
        if active:
            next_order = "asc" if order == "desc" else "desc"
        else:
            next_order = "desc" if key == "date" or key == "start" else "asc"
        headers.append(
            {
                "key": key,
                "label": label,
                "active": active,
                "arrow": ("↓" if order == "desc" else "↑") if active else "",
                "next_order": next_order,
            }
        )
    return headers