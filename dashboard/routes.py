"""Dashboard routes: /, /app/dashboard, /app/dashboard/partial, /app/dashboard/periods-table, /app/dashboard/chart"""

import json
from bottle import request, template
from auth import requires
from dashboard.services import (
    get_periods,
    get_totals,
    get_chart_data,
    get_period_display_params,
)
from config import load_config

config = load_config()


def index():
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/base.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="dashboard",
        **get_period_display_params(periods),
    )


def dashboard():
    # Full page render (like /) — includes base.html with CSS
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/base.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="dashboard",
        **get_period_display_params(periods),
    )


def dashboard_partial():
    """Partial render for htmx tab navigation."""
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/dashboard.html",
        totals=totals,
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        **get_period_display_params(periods),
    )


def dashboard_periods_table():
    """Return the dashboard periods table partial for HTMX refresh."""
    return template(
        "templates/table_periods.html",
        **get_period_display_params(get_periods()),
    )


def dashboard_chart():
    """Return the energy chart partial (lazy-loaded via HTMX)."""
    return template(
        "templates/chart.html",
        chartdata=json.dumps(get_chart_data(get_periods())),
    )


def register_routes(app):
    """Register all dashboard routes with the Bottle app.

    Permissions are declared next to each route; the rules for which role
    holds them live in ``auth/policy.csv``.
    """
    app.get("/")(requires("dashboard", "view")(index))
    app.get("/app/dashboard")(requires("dashboard", "view")(dashboard))
    app.get("/app/dashboard/partial")(requires("dashboard", "view")(dashboard_partial))
    app.get("/app/dashboard/periods-table")(requires("dashboard", "view")(dashboard_periods_table))
    app.get("/app/dashboard/chart")(requires("dashboard", "chart")(dashboard_chart))