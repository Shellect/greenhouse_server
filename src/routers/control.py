"""
Роутер для статуса и настроек управления теплицей.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import strawberry_config
from controller import greenhouse_controller
from database import (
    get_session, get_latest_reading, get_all_devices,
    get_alerts_count, set_device_auto_mode
)
from models import (
    SensorData, DeviceStateResponse, GreenhouseStatus,
    ControlSettings, DeviceType
)

control_router = APIRouter(tags=["Control"])


@control_router.get("/status", response_model=GreenhouseStatus, tags=["Status"])
async def get_greenhouse_status(db: AsyncSession = Depends(get_session)):
    """Получение полного статуса теплицы"""
    latest = await get_latest_reading(db)
    devices = await get_all_devices(db)
    alerts_count = await get_alerts_count(db)

    # Анализируем текущее состояние
    current_data = None
    health_score = 100.0
    recommendations = greenhouse_controller.get_stage_recommendations()

    if latest:
        current_data = SensorData(
            temperature=latest.temperature,
            humidity=latest.humidity,
            soil_moisture=latest.soil_moisture,
            light_level=latest.light_level,
            ph_level=latest.ph_level,
            co2_level=latest.co2_level,
            device_id=latest.device_id
        )
        analysis = greenhouse_controller.analyze_readings(current_data.model_dump())
        health_score = analysis["health_score"]
        recommendations.extend(analysis["recommendations"])

    return GreenhouseStatus(
        current_readings=current_data,
        devices=[DeviceStateResponse.model_validate(d) for d in devices],
        active_alerts=alerts_count,
        growth_stage=greenhouse_controller.current_stage.value,
        health_score=health_score,
        recommendations=recommendations
    )


@control_router.post("/control/settings")
async def update_control_settings(
        settings: ControlSettings,
        db: AsyncSession = Depends(get_session)
):
    """Обновление настроек автоматического контроля"""
    greenhouse_controller.set_growth_stage(settings.growth_stage)

    # Обновляем автоматический режим устройств
    await set_device_auto_mode(db, DeviceType.PUMP.value, settings.auto_watering)
    await set_device_auto_mode(db, DeviceType.FAN.value, settings.auto_ventilation)
    await set_device_auto_mode(db, DeviceType.HEATER.value, settings.auto_heating)
    await set_device_auto_mode(db, DeviceType.LIGHT.value, settings.auto_lighting)

    return {
        "status": "ok",
        "growth_stage": settings.growth_stage.value,
        "auto_watering": settings.auto_watering,
        "auto_ventilation": settings.auto_ventilation,
        "auto_heating": settings.auto_heating,
        "auto_lighting": settings.auto_lighting
    }


@control_router.get("/control/parameters")
async def get_optimal_parameters():
    """Получение оптимальных параметров для клубники"""
    return {
        "temperature": {
            "day": {"min": strawberry_config.TEMP_DAY_MIN, "max": strawberry_config.TEMP_DAY_MAX},
            "night": {"min": strawberry_config.TEMP_NIGHT_MIN, "max": strawberry_config.TEMP_NIGHT_MAX},
            "critical": {"low": strawberry_config.TEMP_CRITICAL_LOW, "high": strawberry_config.TEMP_CRITICAL_HIGH}
        },
        "humidity": {
            "normal": {"min": strawberry_config.HUMIDITY_MIN, "max": strawberry_config.HUMIDITY_MAX},
            "critical": {"low": strawberry_config.HUMIDITY_CRITICAL_LOW,
                         "high": strawberry_config.HUMIDITY_CRITICAL_HIGH}
        },
        "soil_moisture": {
            "normal": {"min": strawberry_config.SOIL_MOISTURE_MIN, "max": strawberry_config.SOIL_MOISTURE_MAX},
            "critical": {"low": strawberry_config.SOIL_MOISTURE_CRITICAL_LOW,
                         "high": strawberry_config.SOIL_MOISTURE_CRITICAL_HIGH}
        },
        "light": {
            "hours": {"min": strawberry_config.LIGHT_HOURS_MIN, "max": strawberry_config.LIGHT_HOURS_MAX},
            "intensity": {"min": strawberry_config.LIGHT_INTENSITY_MIN, "max": strawberry_config.LIGHT_INTENSITY_MAX}
        },
        "ph": {"min": strawberry_config.PH_MIN, "max": strawberry_config.PH_MAX},
        "day_hours": {"start": strawberry_config.DAY_START_HOUR, "end": strawberry_config.DAY_END_HOUR}
    }


