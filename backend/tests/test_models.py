from sqlalchemy import create_engine

from app.core.db import Base
from app import models  # noqa: F401  (register tables)


def test_metadata_creates_on_sqlite():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert {"campaigns", "streams", "offer_states"} <= set(Base.metadata.tables)
