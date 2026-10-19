"""Entry routes: /app/entry, /app/entry/partial, /app/entry/readings-table, /readings"""

import json
from datetime import datetime
from bottle import request, redirect, template
from auth import require_auth
from entry.services import (
    get_display_params,
    validate_reading,
    sortable_headers,
)
from config import load_config

config = load_config()


def entry():
    # Admin users should not see entry - redirect to admin panel
    if request.user["role"] == "admin":
        return redirect("/admin/users")
    # Full page render — includes base.html with CSS
    ctx = get_display_params()
    # Also need totals/chartdata for base.html initial load
    from dashboard.services import get_periods, get_totals, get_chart_data
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/base.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="entry",
        totals=totals,
        chartdata=json.dumps(get_chart_data(periods)),
        **ctx,
    )


def entry_partial():
    """Partial render for htmx tab navigation."""
    ctx = get_display_params()
    return template(
        "templates/entry.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        **ctx,
    )


def entry_readings_table():
    """Return the readings table partial for HTMX refresh."""
    ctx = get_display_params()
    return template("templates/table_readings.html", **ctx)


def add_reading():
    try:
        date_str = request.forms.get("date")
        curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        curr_import = float(request.forms.get("import_units"))
        curr_export = float(request.forms.get("export_units"))
        curr_solar = float(request.forms.get("solar_units"))
    except (ValueError, TypeError):
        return "<div class='alert-error'>❌ Invalid form input format. Please check numeric values.</div>"

    from libsolar import MeterReading
    new_reading = MeterReading(0, curr_date, curr_import, curr_export, curr_solar)

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


def register_routes(app):
    """Register all entry routes with the Bottle app."""
    from auth import require_auth
    app.get("/app/entry")(require_auth()(entry))
    app.get("/app/entry/partial")(require_auth()(entry_partial))
    app.get("/app/entry/readings-table")(require_auth()(entry_readings_table))
    app.post("/readings")(require_auth()(add_reading))