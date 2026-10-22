"""Main entry point for the Solar Tracker application (Quart version)."""

import asyncio
from core.app_quart import create_app, run_app
from config import load_config


async def main():
    """Main entry point."""
    config = load_config()
    app = create_app(config)
    await run_app(app, config)


if __name__ == "__main__":
    asyncio.run(main())