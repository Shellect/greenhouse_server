"""
Репозиторий для работы с оповещениями.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from src.models import Alert


class AlertRepository:
    """Репозиторий для оповещений"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        level: str,
        message: str,
        parameter: Optional[str] = None,
        value: Optional[float] = None
    ) -> Alert:
        """Создание оповещения"""
        alert = Alert(
            level=level,
            message=message,
            parameter=parameter,
            value=value,
            timestamp=datetime.utcnow()
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def get_active(self, limit: int = 50) -> List[Alert]:
        """Получение активных оповещений"""
        result = await self.session.execute(
            select(Alert)
            .where(Alert.acknowledged == False)  # noqa: E712
            .order_by(desc(Alert.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def acknowledge(self, alert_id: int) -> Optional[Alert]:
        """Подтверждение оповещения"""
        result = await self.session.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.acknowledged = True
            await self.session.commit()
            await self.session.refresh(alert)
        return alert

    async def count_active(self) -> int:
        """Подсчёт активных оповещений"""
        result = await self.session.execute(
            select(func.count(Alert.id)).where(Alert.acknowledged == False)  # noqa: E712
        )
        return result.scalar() or 0

