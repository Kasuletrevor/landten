from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from app.core.config import settings

# Create engine with SQLite-specific settings
connect_args = {"check_same_thread": False}  # Required for SQLite
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args=connect_args,
)


def create_db_and_tables():
    """Create all tables - used for development without Alembic"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions"""
    with Session(engine) as session:
        yield session
