"""
Репозиторий для работы с логами роста.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import GrowthLog


class GrowthRepository:
    """Репозиторий для логов роста"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        stage: str,
        notes: Optional[str] = None,
        photo_url: Optional[str] = None
    ) -> GrowthLog:
        """Добавление записи в лог роста"""
        log = GrowthLog(
            stage=stage,
            notes=notes,
            photo_url=photo_url,
            timestamp=datetime.utcnow()
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_all(self, limit: int = 100) -> List[GrowthLog]:
        """Получение логов роста"""
        result = await self.session.execute(
            select(GrowthLog).order_by(desc(GrowthLog.timestamp)).limit(limit)
        )
        return list(result.scalars().all())

