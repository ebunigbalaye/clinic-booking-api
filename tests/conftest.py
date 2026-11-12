import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Booking, BookingAttempt, Slot


@pytest.fixture(scope="session")
def test_engine():
    if not settings.TEST_DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL must be configured")

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with TestingSessionLocal() as session:
        # Clear previous test data.
        session.execute(delete(BookingAttempt))
        session.execute(delete(Booking))
        session.execute(delete(Slot))
        session.commit()

        yield session

        session.rollback()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {
        "X-API-Key": settings.API_KEY,
    }


@pytest.fixture
def sample_slots():
    return [
        {
            "id": "s1",
            "provider": "Dr Ade",
            "start_time": "2099-12-10T09:00:00Z",
            "end_time": "2099-12-10T09:30:00Z",
        },
        {
            "id": "s2",
            "provider": "Dr Bello",
            "start_time": "2099-12-10T10:00:00Z",
            "end_time": "2099-12-10T10:30:00Z",
        },
        {
            "id": "s3",
            "provider": "Dr Ade",
            "start_time": "2099-12-10T11:00:00Z",
            "end_time": "2099-12-10T11:30:00Z",
        },
    ]


@pytest.fixture
def populated_slots(client, auth_headers, sample_slots):
    response = client.post(
        "/reset",
        json={"slots": sample_slots},
        headers=auth_headers,
    )

    assert response.status_code == 200
    return sample_slots


@pytest.fixture
def concurrent_client_factory(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        with TestingSessionLocal() as session:
            yield session

    # Preserve any existing dependency overrides.
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        yield lambda: TestClient(app)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
