"""
Роутер для управления устройствами теплицы.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    get_session, get_all_devices, get_device_state,
    update_device_state, set_device_auto_mode
)
from models import DeviceCommand, DeviceStateResponse, DeviceType

devices_router = APIRouter(prefix="/devices", tags=["Devices"])


@devices_router.get("", response_model=List[DeviceStateResponse])
async def list_devices(db: AsyncSession = Depends(get_session)):
    """Получение списка всех устройств и их состояния"""
    devices = await get_all_devices(db)
    return devices


@devices_router.get("/{device_type}")
async def get_device(
        device_type: DeviceType,
        device_id: str = "main",
        db: AsyncSession = Depends(get_session)
):
    """Получение состояния конкретного устройства"""
    device = await get_device_state(db, device_type.value, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@devices_router.post("/command")
async def send_device_command(
        command: DeviceCommand,
        db: AsyncSession = Depends(get_session)
):
    """Отправка команды устройству (ручное управление)"""
    device = await update_device_state(
        db,
        command.device_type.value,
        command.action.value,
        command.device_id
    )

    # Отключаем автоматический режим при ручном управлении
    await set_device_auto_mode(db, command.device_type.value, False, command.device_id)

    return {
        "status": "ok",
        "device": device.device_type,
        "new_status": device.status,
        "auto_mode": device.auto_mode,
        "message": f"Устройство {device.device_type} переведено в режим: {device.status}"
    }


@devices_router.post("/{device_type}/auto")
async def set_auto_mode(
        device_type: DeviceType,
        enabled: bool = True,
        device_id: str = "main",
        db: AsyncSession = Depends(get_session)
):
    """Включение/выключение автоматического режима устройства"""
    device = await set_device_auto_mode(db, device_type.value, enabled, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "status": "ok",
        "device": device.device_type,
        "auto_mode": device.auto_mode
    }


@devices_router.get("/commands/pending")
async def get_pending_commands(db: AsyncSession = Depends(get_session)):
    """
    Получение очереди команд для NodeMCU.
    NodeMCU периодически опрашивает этот endpoint.
    """
    devices = await get_all_devices(db)
    commands = []

    for device in devices:
        commands.append({
            "device": device.device_type,
            "device_id": device.device_id,
            "action": device.status,
            "auto_mode": device.auto_mode
        })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "commands": commands
    }


