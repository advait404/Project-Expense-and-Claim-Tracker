import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app


@pytest.fixture(scope="function")
def db_session():
    """Create a temporary SQLite database for testing."""
    db_fd, db_path = tempfile.mkstemp()
    database_url = f"sqlite:///{db_path}"

    engine = create_engine(
        database_url, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    yield session
    session.close()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(db_session):
    """Create a test client with dependency override for database."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
