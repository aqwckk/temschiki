import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# тесты работают с отдельной базой, не трогая data.db
TEST_DB = BACKEND_DIR / "test.db"
os.environ["APP_DATABASE_URL"] = "sqlite:///" + TEST_DB.as_posix()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client
