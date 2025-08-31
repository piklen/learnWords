"""
Pytest configuration and fixtures for LearnWords tests
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app
from tests.factories import UserFactory, DocumentFactory, LessonPlanFactory

# 测试数据库URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# 创建测试引擎
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 测试会话工厂
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_settings():
    """Override settings for testing"""
    return get_settings(
        _env_file=".env.test",
        database_url=TEST_DATABASE_URL,
        debug=True,
        testing=True,
    )


# Override dependencies
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Set up test database"""
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=test_engine)
    # Remove test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client"""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_ai_service():
    """Mock AI service"""
    mock = AsyncMock()
    mock.generate_text.return_value = {
        "content": "Generated lesson plan content",
        "success": True,
        "provider": "mock",
        "model": "mock-model",
        "tokens_used": 100,
        "response_time": 0.5,
    }
    return mock


@pytest.fixture
def mock_storage_service():
    """Mock storage service"""
    mock = AsyncMock()
    mock.upload_file.return_value = {
        "success": True,
        "key": "test-file.pdf",
        "url": "https://example.com/test-file.pdf",
        "size": 1024,
        "storage_backend": "mock",
    }
    mock.get_file.return_value = b"mock file content"
    mock.delete_file.return_value = True
    return mock


@pytest.fixture
def mock_celery():
    """Mock Celery tasks"""
    mock = MagicMock()
    mock.delay.return_value.id = "mock-task-id"
    mock.delay.return_value.status = "SUCCESS"
    return mock


@pytest.fixture
def user_factory():
    """User factory fixture"""
    return UserFactory


@pytest.fixture
def document_factory():
    """Document factory fixture"""
    return DocumentFactory


@pytest.fixture
def lesson_plan_factory():
    """Lesson plan factory fixture"""
    return LessonPlanFactory


@pytest.fixture
def test_user(db_session, user_factory):
    """Create a test user"""
    user = user_factory.create(session=db_session)
    db_session.commit()
    return user


@pytest.fixture
def test_document(db_session, document_factory, test_user):
    """Create a test document"""
    document = document_factory.create(session=db_session, user_id=test_user.id)
    db_session.commit()
    return document


@pytest.fixture
def test_lesson_plan(db_session, lesson_plan_factory, test_user, test_document):
    """Create a test lesson plan"""
    lesson_plan = lesson_plan_factory.create(
        session=db_session, 
        user_id=test_user.id,
        document_id=test_document.id
    )
    db_session.commit()
    return lesson_plan


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test user"""
    from app.core.security import create_access_token
    
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set up environment variables for testing"""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("STORAGE_BACKEND", "local")


# Pytest markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
