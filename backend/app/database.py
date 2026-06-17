import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_FILE = (PROJECT_ROOT / "data" / "carbon.db").resolve()
LEGACY_DATA_DIR = (PROJECT_ROOT / "backend" / "data").resolve()


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


def _build_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        if configured_url.startswith("sqlite:///"):
            sqlite_path = Path(configured_url.removeprefix("sqlite:///")).expanduser()
            if not sqlite_path.is_absolute():
                sqlite_path = (PROJECT_ROOT / sqlite_path).resolve()
                return f"sqlite:///{sqlite_path.as_posix()}"
        return configured_url

    configured_data_dir = os.getenv("DATA_DIR")
    if configured_data_dir:
        data_dir = _resolve_project_path(configured_data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(data_dir / 'carbon.db').as_posix()}"

    DEFAULT_DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DATABASE_FILE.as_posix()}"


SQLALCHEMY_DATABASE_URL = _build_database_url()


def _sqlite_file_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None

    sqlite_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
    if str(sqlite_path) == ":memory:":
        return None
    return sqlite_path.resolve()


DATABASE_FILE = _sqlite_file_from_url(SQLALCHEMY_DATABASE_URL)
LEGACY_DATABASE_FILE = (LEGACY_DATA_DIR / "carbon.db").resolve()

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from . import models

    Base.metadata.create_all(bind=engine)
