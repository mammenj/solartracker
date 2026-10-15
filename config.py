"""Configuration management for the Solar Tracker application."""

import argparse
import json
from pathlib import Path
from typing import NamedTuple


class AppConfig(NamedTuple):
    """Application configuration."""

    db_file: Path
    host: str
    port: int
    server: str


def load_config() -> AppConfig:
    """Load host/port/server from config.json and db from CLI or config.json."""
    project_root = Path(__file__).resolve().parent
    config_file = project_root / "config.json"

    defaults = {
        "host": "localhost",
        "port": 8080,
        "server": "gunicorn",
        "db": "meter_logs.db",
    }

    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                defaults.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read config file: {e}")

    parser = argparse.ArgumentParser(
        description="Solar Tracker - Monitor your solar energy readings"
    )
    parser.add_argument(
        "db",
        nargs="?",
        default=defaults.get("db", "meter_logs.db"),
        help="Database filename. Overrides config.json if provided.",
    )

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    return AppConfig(
        db_file=db_path,
        host=defaults.get("host", "localhost"),
        port=defaults.get("port", 8080),
        server=defaults.get("server", "gunicorn"),
    )
