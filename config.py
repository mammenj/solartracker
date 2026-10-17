"""Configuration management for the Solar Tracker application."""

import argparse
import json
import os
from pathlib import Path
from typing import NamedTuple


class AppConfig(NamedTuple):
    """Application configuration."""

    db_file: Path
    host: str
    port: int
    server: str
    app_version: str
    db_name: str


def _load_env(env_file: Path) -> dict:
    """Load key=value pairs from a .env file (manual parsing, no external deps)."""
    env_vars: dict = {}
    if not env_file.exists():
        return env_vars
    try:
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except IOError as e:
        print(f"Warning: Could not read .env file: {e}")
    return env_vars


def load_config() -> AppConfig:
    """Load host/port/server from config.json, version/db from .env and CLI."""
    project_root = Path(__file__).resolve().parent
    config_file = project_root / "config.json"
    env_file = project_root / ".env"

    env_vars = _load_env(env_file)

    defaults = {
        "host": "localhost",
        "port": 8080,
        "server": "gunicorn",
        "db": "meter_logs.db",
        "app_version": env_vars.get("APP_VERSION", "1.0.0"),
        "db_name": env_vars.get("DB_NAME", "meter_logs.db"),
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
        app_version=defaults.get("app_version", "1.0.0"),
        db_name=defaults.get("db_name", "meter_logs.db"),
    )
