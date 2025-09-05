from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from config.settings import settings
from .models import Base


# Create database engine
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class DatabaseManager:
    """Database management class for common operations"""

    def __init__(self):
        self.engine = engine

    def initialize_database(self):
        """Initialize database with tables"""
        create_tables()

    def reset_database(self):
        """Drop and recreate all tables (use with caution!)"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return SessionLocal()

    def close_all_sessions(self):
        """Close all database connections"""
        engine.dispose()
