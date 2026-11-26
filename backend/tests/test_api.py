import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.db import Base
from app.main import app
from app.keitaro.fake import FakeKeitaro
from app import models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.conftest import CATALOG


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    fake = FakeKeitaro(offers=dict(CATALOG))

    def _db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[deps.get_db] = _db
    app.dependency_overrides[deps.get_keitaro] = lambda: fake
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_then_add_and_push(client):
    r = client.post("/api/campaigns",
                    json={"name": "test_quang_api", "geos": ["GM"], "offer_id": 18001})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    streams = client.get(f"/api/campaigns/{cid}/streams").json()
    offers_stream = next(s for s in streams if s["kind"] == "offers")
    sid = offers_stream["id"]
    r = client.post(f"/api/streams/{sid}/offers", json={"offer_id": 18002})
    assert r.status_code == 200
    assert sorted(o["share"] for o in r.json()["offers"]) == [50, 50]
    r = client.post(f"/api/streams/{sid}/push")
    assert r.status_code == 200
    assert r.json()["is_dirty"] is False
