"""Core application factory and setup."""

from bottle import Bottle, default_app
from config import load_config

from auth import register_routes as register_auth_routes, init_auth_db
from dashboard import register_routes as register_dashboard_routes
from entry import register_routes as register_entry_routes
from admin import register_routes as register_admin_routes
from core.deps import send_static
from config import load_config


def create_app(config=None):
    """Create and configure the Bottle application."""
    if config is None:
        config = load_config()

    app = Bottle()

    # Set as default app so routes register correctly
    default_app.push(app)
    try:
        # Initialize auth DB
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