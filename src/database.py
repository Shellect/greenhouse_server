from datetime import datetime, timedelta
from typing import List, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, desc, and_
from sqlalchemy.sql import func

from config import server_config
from models import Base, SensorReading, DeviceState, Alert, GrowthLog, DeviceType

engine = create_async_engine(server_config.DATABASE_URL, echo=server_config.DEBUG, future=True)
async_session_fabric = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализируем устройства по умолчанию
    async with async_session_fabric() as session:
        for device_type in DeviceType:
            existing = await session.execute(
                select(DeviceState).where(
                    DeviceState.device_type == device_type.value
                )
            )
            if not existing.scalar_one_or_none():
                device = DeviceState(
                    device_type=device_type.value,
                    device_id="main",
                    status="off",
                    auto_mode=True
                )
                session.add(device)
        await session.commit()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_fabric() as session:
        try:
            yield session
        except Exception:
            await  session.rollback()
            raise
        finally:
            await session.close()
# ==================== Sensor Operations ====================

async def save_sensor_reading(session: AsyncSession, data: dict) -> SensorReading:
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
    session.add(reading)
    await session.commit()
    await session.refresh(reading)
    return reading


async def get_latest_reading(session: AsyncSession) -> Optional[SensorReading]:
    """Получение последних показаний"""
    result = await session.execute(
        select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(1)
    )
    return result.scalar_one_or_none()


async def get_readings_history(
    session: AsyncSession,
    hours: int = 24,
    limit: int = 1000
) -> List[SensorReading]:
    """Получение истории показаний"""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(SensorReading)
        .where(SensorReading.timestamp >= since)
        .order_by(desc(SensorReading.timestamp))
        .limit(limit)
    )
    return result.scalars().all()


async def get_readings_stats(session: AsyncSession, hours: int = 24) -> dict:
    """Статистика показаний за период"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    result = await session.execute(
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


# ==================== Device Operations ====================

async def get_device_state(
    session: AsyncSession,
    device_type: str,
    device_id: str = "main"
) -> Optional[DeviceState]:
    """Получение состояния устройства"""
    result = await session.execute(
        select(DeviceState).where(
            and_(
                DeviceState.device_type == device_type,
                DeviceState.device_id == device_id
            )
        )
    )
    return result.scalar_one_or_none()


async def get_all_devices(session: AsyncSession) -> List[DeviceState]:
    """Получение всех устройств"""
    result = await session.execute(select(DeviceState))
    return result.scalars().all()


async def update_device_state(
    session: AsyncSession,
    device_type: str,
    status: str,
    device_id: str = "main"
) -> DeviceState:
    """Обновление состояния устройства"""
    device = await get_device_state(session, device_type, device_id)
    
    if not device:
        device = DeviceState(
            device_type=device_type,
            device_id=device_id,
            status=status,
            auto_mode=True
        )
        session.add(device)
    else:
        device.status = status
        device.last_updated = datetime.utcnow()
    
    await session.commit()
    await session.refresh(device)
    return device


async def set_device_auto_mode(
    session: AsyncSession,
    device_type: str,
    auto_mode: bool,
    device_id: str = "main"
) -> DeviceState:
    """Установка автоматического режима устройства"""
    device = await get_device_state(session, device_type, device_id)
    if device:
        device.auto_mode = auto_mode
        device.last_updated = datetime.utcnow()
        await session.commit()
        await session.refresh(device)
    return device


# ==================== Alert Operations ====================

async def create_alert(
    session: AsyncSession,
    level: str,
    message: str,
    parameter: str = None,
    value: float = None
) -> Alert:
    """Создание оповещения"""
    alert = Alert(
        level=level,
        message=message,
        parameter=parameter,
        value=value,
        timestamp=datetime.utcnow()
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_active_alerts(session: AsyncSession, limit: int = 50) -> List[Alert]:
    """Получение активных оповещений"""
    result = await session.execute(
        select(Alert)
        .where(Alert.acknowledged == False)
        .order_by(desc(Alert.timestamp))
        .limit(limit)
    )
    return result.scalars().all()


async def acknowledge_alert(session: AsyncSession, alert_id: int) -> Optional[Alert]:
    """Подтверждение оповещения"""
    result = await session.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if alert:
        alert.acknowledged = True
        await session.commit()
        await session.refresh(alert)
    return alert


async def get_alerts_count(session: AsyncSession) -> int:
    """Подсчёт активных оповещений"""
    result = await session.execute(
        select(func.count(Alert.id)).where(Alert.acknowledged == False)
    )
    return result.scalar()


# ==================== Growth Log Operations ====================

async def add_growth_log(
    session: AsyncSession,
    stage: str,
    notes: str = None,
    photo_url: str = None
) -> GrowthLog:
    """Добавление записи в лог роста"""
    log = GrowthLog(
        stage=stage,
        notes=notes,
        photo_url=photo_url,
        timestamp=datetime.utcnow()
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_growth_logs(session: AsyncSession, limit: int = 100) -> List[GrowthLog]:
    """Получение логов роста"""
    result = await session.execute(
        select(GrowthLog).order_by(desc(GrowthLog.timestamp)).limit(limit)
    )
    return result.scalars().all()





