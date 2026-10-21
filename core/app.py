"""Core application factory and setup."""

from bottle import Bottle, default_app, request, SimpleTemplate
from config import load_config

from auth import register_routes as register_auth_routes, init_auth_db
from auth.policy import can as can_do, reload_policy
from dashboard import register_routes as register_dashboard_routes
from entry import register_routes as register_entry_routes
from admin import register_routes as register_admin_routes
from core.deps import send_static


def create_app(config=None):
    """Create and configure the Bottle application."""
    if config is None:
        config = load_config()

    app = Bottle()

    # Load the Casbin policy and expose can(resource, action) to templates.
    reload_policy()
    SimpleTemplate.defaults["can"] = lambda resource, action: can_do(
        getattr(request, "user", None), resource, action
    )

    # Set as default app so routes register correctly
    default_app.push(app)
    try:
        # Initialize auth DB (also migrates the legacy role CHECK constraint)
        init_auth_db()

        # Register auth routes
        register_auth_routes(app)
        register_dashboard_routes(app)
        register_entry_routes(app)
        register_admin_routes(app)

        # Static files
        app.get("/static/<filename:path>")(send_static)
    finally:
        default_app.pop()

    return app


def run_app(app, config=None):
    """Run the application with the given config."""
    if config is None:
        config = load_config()
    from bottle import run
    run(app, host=config.host, port=config.port, server=config.server, debug=True)