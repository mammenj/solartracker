import functools
import json
from datetime import datetime
from math import ceil
from pathlib import Path

import bottle
from bottle import Bottle, request, response, run, template, static_file, redirect

from config import load_config
from libsolar import EnergyExtrapolator, MeterReading, ReadingPeriod, TotalsDict
from libsolar_sqlite import MeterReadingStore
from auth import (
    init_auth_db,
    create_user,
    get_user,
    get_user_by_id,
    verify_password,
    create_session,
    verify_session,
    list_users,
    update_user,
    count_users,
    ensure_user_db,
)
import os

# Web App Setup
app = Bottle()
BASE_DIR = Path(__file__).resolve().parent

# Load configuration
config = load_config()

# Initialize auth DB
init_auth_db()

db_name = Path(config.db_file).name


def get_user_store() -> MeterReadingStore:
    """Get the MeterReadingStore for the current authenticated user."""
    if not hasattr(request, "store"):
        # Fallback for legacy/compat - uses default DB
        request.store = MeterReadingStore(config.db_file)
    return request.store


def require_auth(roles: list[str] | None = None):
    """Decorator: validate session, check role, inject user + store into request."""
    def decorator(callback):
        @functools.wraps(callback)
        def wrapper(*a, **kw):
            token = request.get_cookie("session")
            user_id = verify_session(token) if token else None
            if not user_id:
                return redirect("/login")
            user = get_user_by_id(user_id)
            if not user or user["status"] != "approved":
                response.delete_cookie("session")
                return redirect("/login?error=not_approved")
            if roles and user["role"] not in roles:
                response.status = 403
                return "Forbidden: insufficient role"
            # Attach user and their store to request
            request.user = user
            request.store = MeterReadingStore(ensure_user_db(user["db_file"]))
            return callback(*a, **kw)
        return wrapper
    return decorator


def get_periods() -> list[ReadingPeriod]:
    """Get all reading periods from the database."""
    readings = get_user_store().load_all()
    return [
        ReadingPeriod(readings[i - 1], readings[i]) for i in range(1, len(readings))
    ]
    # return list(
    # reversed(
    # [
    # ReadingPeriod(readings[i - 1], readings[i])
    # for i in range(1, len(readings))
    # ]
    # )
    # )


def get_readings() -> list[MeterReading]:
    """Get all reading periods from the database."""
    r = get_user_store().load_all()
    r.sort(key=lambda r: r.date, reverse=True)
    return r


def get_periods_with_weekly() -> list[dict]:
    """Get periods with weekly extrapolated values."""
    periods = get_periods()
    return [
        {
            "period": p,
            "extrapolator": EnergyExtrapolator(p),
            "start": p.start,
            "weekly_import": EnergyExtrapolator(p).weekly_import,
            "weekly_export": EnergyExtrapolator(p).weekly_export,
            "weekly_solar": EnergyExtrapolator(p).weekly_solar_yield,
            "weekly_consumption": EnergyExtrapolator(p).weekly_consumption,
            "weekly_balance": EnergyExtrapolator(p).weekly_net_balance,
            "import_diff": p.import_diff,
            "export_diff": p.export_diff,
            "solar_yield": p.solar_yield,
            "consumption": p.consumption,
        }
        for p in periods
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


def validate_reading(new_reading: MeterReading) -> tuple[bool, str]:
    """Validate a new reading against the last stored reading."""
    readings = get_user_store().load_all()
    if not readings:
        return True, ""

    last = readings[-1]
    print("last record", last.date)
    is_present = any(r.date == new_reading.date for r in readings)
    print("date is present >>>>>>>>", is_present)
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
        self_sufficiency = (
            ((consumption - import_diff) / consumption * 100)
            if consumption > 0
            else 0.0
        )
        self_consumption = ((solar - export) / solar * 100) if solar > 0 else 0.0
        points.append(
            {
                "label": p.start.date.strftime("%d/%m/%Y"),
                "solar_gen": round(solar, 2),
                "export": round(export, 2),
                "import": round(import_diff, 2),
                "self_sufficiency_pct": round(self_sufficiency, 1),
                "self_consumption_pct": round(self_consumption, 1),
            }
        )
    return points


@app.get("/")
@require_auth()
def index():
    periods = get_periods()
    totals: TotalsDict = get_totals(periods)
    return template(
        "templates/base.html",
        totals=totals,
        chartdata=json.dumps(get_chart_data(periods)),
        version=config.app_version,
        db_name=db_name,
        user=request.user,
        **get_period_display_params(periods),
    )


@app.get("/app/dashboard/periods-table")
@require_auth()
def dashboard_periods_table():
    """Return the dashboard periods table partial for HTMX refresh."""
    return template(
        "templates/table_periods.html",
        **get_period_display_params(get_periods()),
    )


@app.get("/app/dashboard")
@require_auth()
def dashboard():
    # Compute periods ONCE from the full dataset — totals and the chart are
    # always calculated from every period; only the table display is paged.
    periods = get_periods()
    totals: TotalsDict = get_totals(periods)
    return template(
        "templates/dashboard.html",
        totals=totals,
        chartdata=json.dumps(get_chart_data(periods)),
        version=config.app_version,
        db_name=db_name,
        user=request.user,
        **get_period_display_params(periods),
    )


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


@app.get("/static/<filename:path>")
def send_static(filename):
    # Join the directory path cleanly with your static folder
    static_path = os.path.join(BASE_DIR, "static")
    return static_file(filename, root=static_path)


# --- Auth routes ---

@app.get("/login")
def login_page():
    # Redirect already authenticated users
    token = request.get_cookie("session")
    if token and verify_session(token):
        return redirect("/app/dashboard")
    error = request.params.get("error")
    return template("templates/login.html", error=error, version=config.app_version)


@app.post("/login")
def login_post():
    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        return template("templates/login.html", error="Invalid username or password", version=config.app_version)
    if user["status"] != "approved":
        return template("templates/login.html", error="Account not approved. Contact admin.", version=config.app_version)
    token = create_session(user["id"])
    response.set_cookie("session", token, httponly=True, samesite="Lax", max_age=24*3600, path="/")
    return redirect("/app/dashboard")


@app.post("/logout")
def logout():
    response.delete_cookie("session", path="/")
    return redirect("/login")


# --- Admin user management routes ---

@app.get("/admin/users")
@require_auth(["admin"])
def admin_users():
    from math import ceil
    try:
        page = max(1, int(request.params.get("page", "1")))
    except (ValueError, TypeError):
        page = 1
    sort = request.params.get("sort", "username")
    order = request.params.get("order", "asc")
    users, total = list_users(page, 10, sort, order)
    total_pages = max(1, ceil(total / 10)) if total else 1
    page = min(page, total_pages)

    headers = sortable_headers(sort, order, [
        ("username", "Username"),
        ("full_name", "Full Name"),
        ("role", "Role"),
        ("status", "Status"),
        ("created_at", "Created"),
    ])

    return template(
        "templates/admin_users.html",
        users=users,
        total=total,
        page=page,
        total_pages=total_pages,
        sort=sort,
        order=order,
        headers=headers,
        version=config.app_version,
        db_name=db_name,
    )


@app.get("/admin/users/new")
@require_auth(["admin"])
def admin_user_new():
    return template("templates/admin_user_form.html", user=None, errors=[], version=config.app_version, db_name=db_name)


@app.post("/admin/users")
@require_auth(["admin"])
def admin_user_create():
    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

    errors = []
    if not username:
        errors.append("Username required")
    if get_user(username):
        errors.append("Username already exists")
    if not password:
        errors.append("Password required")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not full_name:
        errors.append("Full name required")
    if role not in ("admin", "user"):
        errors.append("Invalid role")
    if status not in ("pending", "approved", "disabled"):
        errors.append("Invalid status")
    if not db_file:
        errors.append("Database file required")

    if errors:
        return template("templates/admin_user_form.html", user=None, errors=errors, version=config.app_version, db_name=db_name)

    try:
        create_user(username, password, full_name, role, db_file, status)
    except Exception as e:
        return template("templates/admin_user_form.html", user=None, errors=[str(e)], version=config.app_version, db_name=db_name)

    return redirect("/admin/users")


@app.get("/admin/users/<user_id:int>/edit")
@require_auth(["admin"])
def admin_user_edit(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")
    return template("templates/admin_user_form.html", user=user, errors=[], version=config.app_version, db_name=db_name)


@app.post("/admin/users/<user_id:int>")
@require_auth(["admin"])
def admin_user_update(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")

    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

    errors = []
    if not full_name:
        errors.append("Full name required")
    if role not in ("admin", "user"):
        errors.append("Invalid role")
    if status not in ("pending", "approved", "disabled"):
        errors.append("Invalid status")
    if not db_file:
        errors.append("Database file required")

    if errors:
        return template("templates/admin_user_form.html", user=user, errors=errors, version=config.app_version, db_name=db_name)

    update_user(user_id, full_name=full_name, role=role, status=status, db_file=db_file)
    return redirect("/admin/users")


def sortable_headers(sort: str, order: str, fields: list[tuple[str, str]]) -> list[dict]:
    """
    Build sortable column-header metadata for htmx-clickable <th> elements.

    Each dict has: key, label, active (bool), arrow (↑/↓ on active column),
    next_order (clicked sort toggles asc/desc; new column gets its default).
    """
    headers = []
    for key, label in fields:
        active = key == sort
        if active:
            next_order = "asc" if order == "desc" else "desc"
        else:
            # Date-type columns default to descending (newest first),
            # numeric columns to ascending.
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


def get_display_params() -> dict:
    """
    Parse paging/sorting query params for the readings list and fetch the page
    from the store (all paging/sorting happens server-side, in Python/SQL).

    Returns dict with: readings, total, page, page_size, total_pages,
    sort, order, headers.
    """
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


def get_period_display_params(periods: list[ReadingPeriod]) -> dict:
    """
    Build a paged, sorted slice of period rows for display only.
    All calculations (totals, chart) are done on the full `periods` list —
    this only affects what the table shows.
    """
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


@app.get("/app/entry")
@require_auth(["admin"])
def entry():
    ctx = get_display_params()
    return template(
        "templates/entry.html",
        version=config.app_version,
        db_name=db_name,
        user=request.user,
        **ctx,
    )


@app.get("/app/entry/readings-table")
@require_auth(["admin"])
def entry_readings_table():
    """Return the readings table partial for HTMX refresh."""
    ctx = get_display_params()
    return template("templates/table_readings.html", **ctx)


@app.post("/readings")
@require_auth(["admin"])
def add_reading():
    try:
        date_str = request.forms.get("date")
        curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        curr_import = float(request.forms.get("import_units"))
        curr_export = float(request.forms.get("export_units"))
        curr_solar = float(request.forms.get("solar_units"))
    except (ValueError, TypeError):
        return "<div class='alert-error'>❌ Invalid form input format. Please check numeric values.</div>"

    new_reading = MeterReading(0, curr_date, curr_import, curr_export, curr_solar)
    # removing validation

    is_valid, err_msg = validate_reading(new_reading)
    if not is_valid:
        return f"<div class='alert-error'>❌ {err_msg}</div>"

    is_update = get_user_store().save_or_update(new_reading)

    msg = (
        f"✓ Updated record for {curr_date.strftime('%d-%b-%Y')}."
        if is_update
        else f"✓ Recorded reading for {curr_date.strftime('%d-%b-%Y')}"
    )

    return f"<div class='alert-success'>{msg}</div>"


def main():
    run(app, host=config.host, port=config.port, server=config.server, debug=True)


if __name__ == "__main__":
    main()
