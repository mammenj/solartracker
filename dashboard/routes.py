"""Dashboard routes: /, /app/dashboard, /app/dashboard/partial, /app/dashboard/periods-table"""

import json
from bottle import request, redirect, template
from auth import require_auth
from dashboard.services import (
    get_periods,
    get_totals,
    get_chart_data,
    get_period_display_params,
)
from config import load_config

config = load_config()


def index():
    # Admin users should not see dashboard - redirect to admin panel
    if request.user["role"] == "admin":
        return redirect("/admin/users")
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/base.html",
        totals=totals,
        chartdata=json.dumps(get_chart_data(periods)),
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="dashboard",
        **get_period_display_params(periods),
    )


def dashboard():
    # Admin users should not see dashboard - redirect to admin panel
    if request.user["role"] == "admin":
        return redirect("/admin/users")
    # Full page render (like /) — includes base.html with CSS
    periods = get_periods()
    totals = get_totals(periods)
    return template(
        "templates/base.html",
        totals=totals,
        chartdata=json.dumps(get_chart_data(periods)),
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
        chartdata=json.dumps(get_chart_data(periods)),
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


def register_routes(app):
    """Register all dashboard routes with the Bottle app."""
    from auth import require_auth
    app.get("/")(require_auth()(index))
    app.get("/app/dashboard")(require_auth()(dashboard))
    app.get("/app/dashboard/partial")(require_auth()(dashboard_partial))
    app.get("/app/dashboard/periods-table")(require_auth()(dashboard_periods_table))