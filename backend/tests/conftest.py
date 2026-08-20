import os
import tempfile
import pytest

# Respect an externally-provided DATABASE_URL (e.g. for running the suite
# against real Postgres in CI or local verification). Falls back to a fresh
# SQLite file per session so `pytest` works with zero external setup.
if "DATABASE_URL" not in os.environ:
    _db_fd, _db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)
