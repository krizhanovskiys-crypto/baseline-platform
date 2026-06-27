"""Generic async repository providing basic CRUD operations."""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository.  Subclass and set ``model`` class attribute."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, record_id: int) -> ModelT | None:
        """Return a single record by primary key or None."""
        return await self._session.get(self.model, record_id)

    async def get_all(self) -> list[ModelT]:
        """Return all records (use with care on large tables)."""
        result = await self._session.execute(select(self.model))
        return list(result.scalars().all())

    async def add(self, instance: ModelT) -> ModelT:
        """Persist a new instance (does not commit — caller owns transaction)."""
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete an instance (does not commit — caller owns transaction)."""
        await self._session.delete(instance)
        await self._session.flush()

    async def _first(self, *where: Any) -> ModelT | None:
        stmt = select(self.model).where(*where)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def _all(self, *where: Any) -> list[ModelT]:
        stmt = select(self.model).where(*where)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
