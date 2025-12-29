"""
Репозиторий для работы с показаниями датчиков.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from src.models import SensorReading


class SensorRepository:
    """Репозиторий для показаний датчиков"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, data: dict) -> SensorReading:
        """Сохранение показаний датчиков"""
        reading = SensorReading(
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            soil_moisture=data.get("soil_moisture"),
            light_level=data.get("light_level"),
            ph_level=data.get("ph_level"),
            co2_level=data.get("co2_level"),
            device_id=data.get("device_id", "nodemcu-1"),
            timestamp=datetime.utcnow()
        )
        self.session.add(reading)
        await self.session.commit()
        await self.session.refresh(reading)
        return reading

    async def get_latest(self) -> Optional[SensorReading]:
        """Получение последних показаний"""
        result = await self.session.execute(
            select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, hours: int = 24, limit: int = 1000) -> List[SensorReading]:
        """Получение истории показаний"""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(SensorReading)
            .where(SensorReading.timestamp >= since)
            .order_by(desc(SensorReading.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self, hours: int = 24) -> dict:
        """Статистика показаний за период"""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(
                func.avg(SensorReading.temperature).label("avg_temp"),
                func.min(SensorReading.temperature).label("min_temp"),
                func.max(SensorReading.temperature).label("max_temp"),
                func.avg(SensorReading.humidity).label("avg_humidity"),
                func.avg(SensorReading.soil_moisture).label("avg_soil_moisture"),
                func.avg(SensorReading.light_level).label("avg_light"),
                func.count(SensorReading.id).label("count")
            ).where(SensorReading.timestamp >= since)
        )

        row = result.one()
        return {
            "period_hours": hours,
            "readings_count": row.count,
            "temperature": {
                "avg": round(row.avg_temp, 1) if row.avg_temp else None,
                "min": round(row.min_temp, 1) if row.min_temp else None,
                "max": round(row.max_temp, 1) if row.max_temp else None
            },
            "humidity_avg": round(row.avg_humidity, 1) if row.avg_humidity else None,
            "soil_moisture_avg": round(row.avg_soil_moisture, 1) if row.avg_soil_moisture else None,
            "light_avg": round(row.avg_light, 1) if row.avg_light else None
        }

