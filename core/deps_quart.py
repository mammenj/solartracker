"""Core dependencies and utilities for Quart."""

import os
from pathlib import Path
from quart import send_from_directory

from config import load_config

config = load_config()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "static"


async def send_static(filename: str):
    """Serve static files."""
    return await send_from_directory(STATIC_DIR, filename)