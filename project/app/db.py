from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import Settings

settings = Settings()
DATABASE_URL = settings.DATABASE_URL
async_engine = create_async_engine(DATABASE_URL, echo=True, future=True)


async def get_session() -> AsyncSession:  # type: ignore
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
