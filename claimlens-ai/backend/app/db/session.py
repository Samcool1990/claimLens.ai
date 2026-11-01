from collections.abc import Generator
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from ..core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
url = settings.database_url
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def enable_sqlite_fks(dbapi_connection, connection_record):
    if url.startswith("sqlite"):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


def init_db() -> None:
    if url.startswith("sqlite:///"):
        raw = url.removeprefix("sqlite:///")
        if raw != ":memory:":
            Path(raw).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    if url.startswith("sqlite"):
        with engine.begin() as connection:
            clause_columns = {
                row._mapping["name"]
                for row in connection.exec_driver_sql("PRAGMA table_info(clauses)")
            }
            if clause_columns and "clause_type" not in clause_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE clauses ADD COLUMN clause_type VARCHAR(32) NOT NULL DEFAULT 'unknown'"
                )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
