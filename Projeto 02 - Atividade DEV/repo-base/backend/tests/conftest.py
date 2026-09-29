"""Fixtures compartilhadas: cada teste roda contra um SQLite em memória isolado.

Assim os testes nunca tocam o `rocketlab.db` de desenvolvimento.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys, get_db
from app.main import app
from app.movies import models  # noqa: F401  Registra os modelos ORM.


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,  # mantém uma única conexão (necessário p/ SQLite em memória)
        connect_args={"check_same_thread": False},
    )
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()