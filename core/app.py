"""Core Quart application factory and setup."""

from quart import Quart, request
from config import load_config
from pathlib import Path

from auth.policy import can as can_do, reload_policy
from auth.routes import register_routes as register_auth_routes
from dashboard.routes import register_routes as register_dashboard_routes
from entry.routes import register_routes as register_entry_routes
from admin.routes import register_routes as register_admin_routes


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _format_float(value, precision: int = 2) -> str:
    """Render a number with a fixed number of decimals (e.g. 10 -> '10.00')."""
    try:
        return f"{float(value):.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


def create_app(config=None):
    """Create and configure the Quart application."""
    if config is None:
        config = load_config()

    app = Quart(
        __name__,
        static_folder=str(PROJECT_ROOT / "static"),
        static_url_path="/static",
        template_folder=str(PROJECT_ROOT),
    )

    # Load the Casbin policy and expose can(resource, action) to templates.
    reload_policy()
    app.jinja_env.globals["can"] = lambda resource, action: can_do(
        getattr(request, "user", None), resource, action
    )
    app.jinja_env.filters["format_float"] = _format_float

    # Register routes
    register_auth_routes(app)
    register_dashboard_routes(app)
    register_entry_routes(app)
    register_admin_routes(app)

    @app.teardown_request
    async def _close_request_store(exc):
        """Close the per-request meter-reading store's connection."""
        store = getattr(request, "store", None)
        if store is not None:
            try:
                await store.aclose()
            except Exception:
                pass

    # Health check endpoint for testing
    @app.route("/health")
    async def health():
        return {"status": "ok", "framework": "quart"}

    return app


async def run_app(app, config=None):
    """Run the application with the given config using Hypercorn."""
    if config is None:
        config = load_config()

    from hypercorn.asyncio import serve
    from hypercorn.config import Config as HypercornConfig

    hconfig = HypercornConfig()
    hconfig.bind = [f"{config.host}:{config.port}"]

    await serve(app, hconfig)