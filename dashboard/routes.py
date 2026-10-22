"""Dashboard routes: /, /app/dashboard, /app/dashboard/partial, /app/dashboard/periods-table, /app/dashboard/chart (Quart version)."""

import json
from quart import request, render_template
from auth.deps import requires
from dashboard.services import (
    get_periods,
    get_totals,
    get_chart_data,
    get_period_display_params,
)
from config import load_config

config = load_config()


async def index():
    periods = await get_periods()
    totals = await get_totals(periods)
    return await render_template(
        "templates/base.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="dashboard",
        **await get_period_display_params(periods),
    )


async def dashboard():
    # Full page render (like /) — includes base.html with CSS
    periods = await get_periods()
    totals = await get_totals(periods)
    return await render_template(
        "templates/base.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="dashboard",
        **await get_period_display_params(periods),
    )


async def dashboard_partial():
    """Partial render for htmx tab navigation."""
    periods = await get_periods()
    totals = await get_totals(periods)
    return await render_template(
        "templates/dashboard.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        **await get_period_display_params(periods),
    )


async def dashboard_periods_table():
    """Return the dashboard periods table partial for HTMX refresh."""
    return await render_template(
        "templates/table_periods.html",
        **await get_period_display_params(await get_periods()),
    )


async def dashboard_chart():
    """Return the energy chart partial (lazy-loaded via HTMX)."""
    return await render_template(
        "templates/chart.html",
        chartdata=json.dumps(await get_chart_data(await get_periods())),
    )


def register_routes(app):
    """Register all dashboard routes with the Quart app."""
    app.add_url_rule("/", view_func=requires("dashboard", "view")(index), methods=["GET"])
    app.add_url_rule("/app/dashboard", view_func=requires("dashboard", "view")(dashboard), methods=["GET"])
    app.add_url_rule("/app/dashboard/partial", view_func=requires("dashboard", "view")(dashboard_partial), methods=["GET"])
    app.add_url_rule("/app/dashboard/periods-table", view_func=requires("dashboard", "view")(dashboard_periods_table), methods=["GET"])
    app.add_url_rule("/app/dashboard/chart", view_func=requires("dashboard", "chart")(dashboard_chart), methods=["GET"])