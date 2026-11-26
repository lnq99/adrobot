import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app import models  # noqa: F401
from app.keitaro.fake import FakeKeitaro

CATALOG = {
    18001: {"id": 18001, "name": "18001 Offer A", "country": ["CL"]},
    18002: {"id": 18002, "name": "18002 Offer B", "country": ["TH"]},
    18003: {"id": 18003, "name": "18003 Offer C", "country": ["CO"]},
    18004: {"id": 18004, "name": "18004 Offer D", "country": ["BR"]},
    18005: {"id": 18005, "name": "18005 Offer E", "country": ["PE"]},
    18006: {"id": 18006, "name": "18006 Offer F", "country": ["MX"]},
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def keitaro():
    return FakeKeitaro(offers=dict(CATALOG))
