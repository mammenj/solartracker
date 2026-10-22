"""Entry routes: /app/entry, /app/entry/partial, /app/entry/readings-table, /readings (Quart version)."""

from datetime import datetime
from quart import request, render_template
from auth.deps_quart import requires
from auth.deps_quart import get_user_store
from entry.services_quart import (
    get_display_params,
    validate_reading,
    sortable_headers,
)
from config import load_config

config = load_config()


async def entry():
    # Full page render — includes base.html with CSS
    ctx = await get_display_params()
    # Also need totals for base.html initial load
    from dashboard.services_quart import get_periods, get_totals
    periods = await get_periods()
    totals = await get_totals(periods)
    return await render_template(
        "templates/base.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="entry",
        totals=totals,
        **ctx,
    )


async def entry_partial():
    """Partial render for htmx tab navigation."""
    ctx = await get_display_params()
    return await render_template(
        "templates/entry.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        **ctx,
    )


async def entry_readings_table():
    """Return the readings table partial for HTMX refresh."""
    ctx = await get_display_params()
    return await render_template("templates/table_readings.html", **ctx)


async def add_reading():
    try:
        form = await request.form
        date_str = form.get("date")
        curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        curr_import = float(form.get("import_units"))
        curr_export = float(form.get("export_units"))
        curr_solar = float(form.get("solar_units"))
    except (ValueError, TypeError):
        return "<div class='alert-error'>❌ Invalid form input format. Please check numeric values.</div>"

    from libsolar import MeterReading
    new_reading = MeterReading(0, curr_date, curr_import, curr_export, curr_solar)

    is_valid, err_msg = await validate_reading(new_reading)
    if not is_valid:
        return f"<div class='alert-error'>❌ {err_msg}</div>"

    store = await get_user_store()
    is_update = store.save_or_update(new_reading)

    msg = (
        f"✓ Updated record for {curr_date.strftime('%d-%b-%Y')}."
        if is_update
        else f"✓ Recorded reading for {curr_date.strftime('%d-%b-%Y')}"
    )

    return f"<div class='alert-success'>{msg}</div>"


def register_routes(app):
    """Register all entry routes with the Quart app."""
    app.add_url_rule("/app/entry", view_func=requires("entry", "view")(entry), methods=["GET"])
    app.add_url_rule("/app/entry/partial", view_func=requires("entry", "view")(entry_partial), methods=["GET"])
    app.add_url_rule("/app/entry/readings-table", view_func=requires("entry", "view")(entry_readings_table), methods=["GET"])
    app.add_url_rule("/readings", view_func=requires("entry", "write")(add_reading), methods=["POST"])