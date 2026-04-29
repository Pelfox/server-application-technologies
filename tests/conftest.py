from collections.abc import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.session import sessionmaker as SessionMaker

from app.__main__ import app
from app.config import get_settings
from app.database import Base, get_session


@pytest.fixture
def session_factory() -> Generator[SessionMaker[Session], None, None]:
    schema_name = f"test_{uuid4().hex}"
    database_url = get_settings().database_url
    maintenance_engine = create_engine(database_url, pool_pre_ping=True)

    with maintenance_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    test_engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema_name}"},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=test_engine)
    testing_session_local = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    try:
        yield testing_session_local
    finally:
        test_engine.dispose()
        with maintenance_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        maintenance_engine.dispose()


@pytest.fixture
def session(session_factory: SessionMaker[Session]) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def faker() -> Faker:
    return Faker()


@pytest.fixture
def client(session_factory: SessionMaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(
    session_factory: SessionMaker[Session],
) -> Generator[AsyncClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
