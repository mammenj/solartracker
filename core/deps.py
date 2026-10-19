"""Core dependencies and utilities."""

from bottle import static_file
from config import load_config
import os

config = load_config()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def send_static(filename):
    """Serve static files."""
    static_path = os.path.join(BASE_DIR, "..", "static")
    return static_file(filename, root=static_path)