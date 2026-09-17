"""Pytest entrypoint.

Discovers the app's models so SQLAlchemy metadata is fully populated before the schema
is built, then re-exports every fixture.
"""

import os

os.environ.setdefault("ENV", "testing")  # resolve app.config.config to TestConfig before importing app

from pathlib import Path  # noqa: E402

import app  # noqa: E402
from app.platform.utils.discovery import discover_and_import  # noqa: E402

discover_and_import(["models.py", "models/**/*.py"], search_root=Path(app.__file__).parent)

from tests.fixtures import *  # noqa: E402, F401, F403
