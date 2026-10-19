"""Main entry point for the Solar Tracker application."""

from core.app import create_app, run_app
from config import load_config


def main():
    """Main entry point."""
    config = load_config()
    app = create_app(config)
    run_app(app, config)


if __name__ == "__main__":
    main()