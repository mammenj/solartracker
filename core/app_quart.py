"""Core Quart application factory and setup."""

from quart import Quart, request
from config import load_config

from auth.policy import can as can_do, reload_policy


def create_app(config=None):
    """Create and configure the Quart application."""
    if config is None:
        config = load_config()

    # Use project root's static folder for static files
    import os
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    static_folder = project_root / "static"

    app = Quart(__name__, static_folder=str(static_folder), static_url_path="/static")

    # Load the Casbin policy and expose can(resource, action) to templates.
    reload_policy()
    app.jinja_env.globals["can"] = lambda resource, action: can_do(
        getattr(request, "user", None), resource, action
    )

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
    hconfig.debug = True

    await serve(app, hconfig)