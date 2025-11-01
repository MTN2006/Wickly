# wickly/db.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Dev DB (SQLite file in project root). Switch to Postgres later.
DATABASE_URL = "sqlite+aiosqlite:///./wickly.db"
# Postgres later example:
# DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/wickly"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
    """
    FastAPI dependency that gives you an AsyncSession per request.
    """
    async with AsyncSessionLocal() as session:
        yield session


