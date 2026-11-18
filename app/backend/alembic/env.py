import os

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (register tables)
from app.core.config import get_settings
from app.db import Base

target_metadata = Base.metadata


def _url() -> str:
    return os.environ.get("AUTOCARE_MIGRATE_URL") or get_settings().database_url


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
