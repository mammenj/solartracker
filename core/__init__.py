"""Core package initialization."""

from core.app import create_app, run_app
from core.deps import send_static

__all__ = [
    "create_app",
    "run_app",
    "send_static",
]