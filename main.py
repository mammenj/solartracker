"""Main entry point for the Solar Tracker application."""

import asyncio
from core.app import create_app, run_app
from auth.db import init_auth_db
from config import load_config


async def _run() -> None:
    """Build and serve the application."""
    config = load_config()
    app = create_app(config)
    await init_auth_db()
    await run_app(app, config)


def main() -> None:
    """Synchronous console-script entry point."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
