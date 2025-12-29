"""
Роутер для работы с датчиками.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.controller import greenhouse_controller
from src.database import get_session
from src.models import SensorData, SensorDataResponse
from src.repositories import SensorRepository, DeviceRepository, AlertRepository

sensors_router = APIRouter(prefix='/sensors', tags=["Sensors"])


@sensors_router.post('/data', response_model=dict)
async def receive_sensor_data(data: SensorData, db: AsyncSession = Depends(get_session)):
    """
    Приём данных с датчиков NodeMCU.
    При первом подключении контроллера — регистрирует его устройства.
    Анализирует данные и возвращает команды для устройств.
    """
    sensor_repo = SensorRepository(db)
    device_repo = DeviceRepository(db)
    alert_repo = AlertRepository(db)

    # Регистрируем контроллер при первом подключении
    if not await device_repo.is_controller_registered(data.device_id):
        await device_repo.register_controller(data.device_id)

    # Сохраняем показания
    reading = await sensor_repo.save(data.model_dump())

    # Анализируем и получаем команды
    analysis = greenhouse_controller.analyze_readings(data.model_dump())

    # Сохраняем оповещения
    for alert_data in analysis["alerts"]:
        await alert_repo.create(
            level=alert_data["level"].value,
            message=alert_data["message"],
            parameter=alert_data.get("parameter"),
            value=alert_data.get("value")
        )

    # Обновляем состояние устройств на основе команд
    commands_for_device = []
    for cmd in analysis["commands"]:
        device = await device_repo.get_by_type(cmd.device_type.value, cmd.device_id)
        if device and device.auto_mode:
            await device_repo.update_status(cmd.device_type.value, cmd.action.value, cmd.device_id)
            commands_for_device.append({
                "device": cmd.device_type.value,
                "action": cmd.action.value,
                "duration": cmd.duration
            })

    return {
        "status": "ok",
        "reading_id": reading.id,
        "timestamp": reading.timestamp.isoformat(),
        "commands": commands_for_device,
        "health_score": analysis["health_score"],
        "is_daytime": analysis["is_daytime"]
    }


@sensors_router.get("/latest", response_model=Optional[SensorDataResponse])
async def get_latest_sensor_data(db: AsyncSession = Depends(get_session)):
    """Получение последних показаний датчиков"""
    sensor_repo = SensorRepository(db)
    reading = await sensor_repo.get_latest()
    if not reading:
        raise HTTPException(status_code=404, detail="No sensor data available")
    return reading


@sensors_router.get("/history")
async def get_sensor_history(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_session)
):
    """Получение истории показаний за указанный период"""
    sensor_repo = SensorRepository(db)
    readings = await sensor_repo.get_history(hours=hours)
    return {
        "period_hours": hours,
        "count": len(readings),
        "readings": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "temperature": r.temperature,
                "humidity": r.humidity,
                "soil_moisture": r.soil_moisture,
                "light_level": r.light_level,
                "ph_level": r.ph_level,
                "co2_level": r.co2_level
            }
            for r in readings
        ]
    }


@sensors_router.get("/stats")
async def get_sensor_stats(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_session)
):
    """Статистика показаний за период"""
    sensor_repo = SensorRepository(db)
    return await sensor_repo.get_stats(hours=hours)
