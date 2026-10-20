"""Dashboard service functions for computing periods, totals, chart data, etc."""

from math import ceil
from bottle import request
from auth.deps import get_user_store
from libsolar import EnergyExtrapolator, MeterReading, ReadingPeriod, TotalsDict


# Sortable fields for the dashboard Period Summaries table
PERIOD_SORT_FIELDS = [
    ("start", "Period"),
    ("days", "Days"),
    ("import", "Import(kWh)"),
    ("export", "Export(kWh)"),
    ("net", "Net(kWh)"),
    ("consumption", "Use(kWh/d)"),
]

PERIOD_SORT_KEYS = {
    "start": lambda r: r["start"],
    "days": lambda r: r["days"],
    "import": lambda r: r["import"],
    "export": lambda r: r["export"],
    "net": lambda r: r["net"],
    "consumption": lambda r: r["consumption"],
}


def get_periods() -> list[ReadingPeriod]:
    """Get all reading periods from the database."""
    readings = get_user_store().load_all()
    return [
        ReadingPeriod(readings[i - 1], readings[i]) for i in range(1, len(readings))
    ]


def get_totals(periods: list[ReadingPeriod] | None = None) -> TotalsDict:
    """Calculate totals from all periods (periods computed here if not given)."""
    if periods is None:
        periods = get_periods()
    return {
        "total_days": sum(p.days for p in periods),
        "total_import": sum(p.import_diff for p in periods),
        "total_export": sum(p.export_diff for p in periods),
        "total_solar": sum(p.solar_yield for p in periods),
        "total_balance": sum(p.net_balance for p in periods),
        "total_consumption": sum(p.consumption for p in periods),
    }


def get_chart_data(periods: list[ReadingPeriod] | None = None):
    """Return chart-ready data for the dashboard energy chart (full dataset)."""
    if periods is None:
        periods = get_periods()
    points = []
    for p in periods:
        solar = p.solar_yield
        consumption = p.consumption
        export = p.export_diff
        import_diff = p.import_diff
        days = p.days
        self_sufficiency = (
            ((consumption - import_diff) / consumption * 100)
            if consumption > 0
            else 0.0
        )
        self_consumption = ((solar - export) / solar * 100) if solar > 0 else 0.0
        grid_dependency = (import_diff / consumption * 100) if consumption > 0 else 0.0
        export_ratio = (export / solar * 100) if solar > 0 else 0.0
        points.append(
            {
                # Existing fields (kept for backward compatibility)
                "label": p.start.date.strftime("%d/%m/%Y"),
                "solar_gen": round(solar, 2),
                "export": round(export, 2),
                "import": round(import_diff, 2),
                "self_sufficiency_pct": round(self_sufficiency, 1),
                "self_consumption_pct": round(self_consumption, 1),
                # Phase 1 derived fields
                "net_balance": round(p.net_balance, 2),
                "consumption": round(consumption, 2),
                "days": days,
                "solar_per_day": round(solar / days, 2) if days > 0 else 0.0,
                "import_per_day": round(import_diff / days, 2) if days > 0 else 0.0,
                "export_per_day": round(export / days, 2) if days > 0 else 0.0,
                "consumption_per_day": round(consumption / days, 2) if days > 0 else 0.0,
                "self_consumed": round(solar - export, 2),
                "grid_dependency_pct": round(grid_dependency, 1),
                "export_ratio_pct": round(export_ratio, 1),
            }
        )
    return points


def get_period_display_params(periods: list[ReadingPeriod]) -> dict:
    """
    Build a paged, sorted slice of period rows for display only.
    All calculations (totals, chart) are done on the full `periods` list —
    this only affects what the table shows.
    """
    from math import ceil
    try:
        page = max(1, int(request.params.get("page", "1")))
    except (ValueError, TypeError):
        page = 1

    sort = request.params.get("sort", "start")
    order = request.params.get("order", "desc")
    if sort not in PERIOD_SORT_KEYS:
        sort = "start"
    if order not in ("asc", "desc"):
        order = "desc"

    # Flatten each period into a plain row (computed once, full dataset)
    rows = [
        {
            "start": p.start.date,
            "end": p.end.date,
            "days": p.days,
            "import": p.import_diff,
            "export": p.export_diff,
            "net": p.net_balance,
            "consumption": p.consumption,
            "avg": p.avg_daily_consumption,
        }
        for p in periods
    ]

    rows.sort(key=PERIOD_SORT_KEYS[sort], reverse=(order == "desc"))

    page_size = 10
    total = len(rows)
    total_pages = max(1, ceil(total / page_size)) if total else 1
    page = min(page, total_pages)
    paged = rows[(page - 1) * page_size : page * page_size]

    # Import sortable_headers from admin services to avoid circular import
    from admin.services import sortable_headers

    return {
        "periods": paged,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "sort": sort,
        "order": order,
        "headers": sortable_headers(sort, order, PERIOD_SORT_FIELDS),
    }