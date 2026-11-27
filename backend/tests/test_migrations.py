import pathlib

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.db import Base
from app import models  # noqa: F401  (registers tables on Base.metadata)

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _schema(engine) -> dict[str, list[str]]:
    insp = inspect(engine)
    return {
        table: sorted(c["name"] for c in insp.get_columns(table))
        for table in insp.get_table_names()
        if table != "alembic_version"
    }


def test_migrations_match_models(tmp_path, monkeypatch):
    """`alembic upgrade head` must build exactly the schema the models declare.
    Catches a model change that forgot its migration (and vice versa)."""
    from app.core import config as config_module

    mig_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    # env.py sets the url from settings.database_url, so point that at a temp sqlite.
    monkeypatch.setattr(config_module.settings, "database_url", mig_url)

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    migrated = _schema(create_engine(mig_url))

    model_engine = create_engine("sqlite://")
    Base.metadata.create_all(model_engine)
    declared = _schema(model_engine)

    assert migrated == declared
