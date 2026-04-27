"""Database connection and session management.

Sets up SQLAlchemy engine, session factory, and the declarative base for ORM models.
Provides a FastAPI dependency (get_db) that yields a session for each request.
"""

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.common_constants import DATABASE_URL

# Create engine with SQLite connection (check_same_thread=False allows multi-threaded access in dev)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
logger.info(f"Database engine created: {DATABASE_URL}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session for the request lifespan.

    Opens a new SessionLocal instance, yields it to the route handler, and closes
    it in a finally block to ensure cleanup even if the route raises an exception.
    """
    logger.debug("Opening database session")
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Unexpected error during database session: {e!r}")
        raise
    finally:
        db.close()
        logger.debug("Closed database session")
