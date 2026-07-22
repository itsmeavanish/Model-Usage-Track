"""
Pytest fixtures: in-memory SQLite + isolated settings per test.

We import and set up the engine AFTER overriding settings.database_url, so that
each test module gets a clean DB. The two important things this conftest does:

1. Forces the test settings to use an in-memory SQLite URL via env vars BEFORE
   any app module is imported by the test file.
2. Provides an async session + initializes the schema for each test.
"""
import os
import asyncio
from typing import AsyncGenerator

# Force in-memory SQLite BEFORE app modules are imported.
os.environ["GLM_MONITOR_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["GLM_MONITOR_USER_IDENTITY"] = "me@example.com"
os.environ["GLM_MONITOR_USER_APPLICATION"] = "opencode"
os.environ["GLM_MONITOR_POLL_INTERVAL_SECONDS"] = "999999"
# Never start real network servers (proxy) inside the test event loop.
os.environ["GLM_MONITOR_PROXY_ENABLED"] = "false"
os.environ["GLM_MONITOR_ANTHROPIC_PROXY_ENABLED"] = "false"
os.environ.setdefault("GLM_MONITOR_ZAI_API_KEY", "test_key")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base
import app.models  # noqa: F401


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
