"""
Репозиторий для работы с устройствами.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import DeviceState, DeviceType


class DeviceRepository:
    """Репозиторий для устройств"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_type(self, device_type: str, device_id: str = "main") -> Optional[DeviceState]:
        """Получение состояния устройства"""
        result = await self.session.execute(
            select(DeviceState).where(
                and_(
                    DeviceState.device_type == device_type,
                    DeviceState.device_id == device_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[DeviceState]:
        """Получение всех устройств"""
        result = await self.session.execute(select(DeviceState))
        return list(result.scalars().all())

    async def get_by_controller(self, controller_id: str) -> List[DeviceState]:
        """Получение устройств конкретного контроллера"""
        result = await self.session.execute(
            select(DeviceState).where(DeviceState.device_id == controller_id)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        device_type: str,
        status: str,
        device_id: str = "main"
    ) -> DeviceState:
        """Обновление состояния устройства"""
        device = await self.get_by_type(device_type, device_id)

        if not device:
            device = DeviceState(
                device_type=device_type,
                device_id=device_id,
                status=status,
                auto_mode=True
            )
            self.session.add(device)
        else:
            device.status = status
            device.last_updated = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def set_auto_mode(
        self,
        device_type: str,
        auto_mode: bool,
        device_id: str = "main"
    ) -> Optional[DeviceState]:
        """Установка автоматического режима устройства"""
        device = await self.get_by_type(device_type, device_id)
        if device:
            device.auto_mode = auto_mode
            device.last_updated = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(device)
        return device

    async def register_controller(self, controller_id: str) -> List[DeviceState]:
        """
        Регистрация нового контроллера NodeMCU.
        Создаёт записи для всех типов устройств этого контроллера.
        Вызывается при первом получении данных от контроллера.
        
        Returns:
            Список созданных/существующих устройств
        """
        devices = []
        
        for device_type in DeviceType:
            existing = await self.session.execute(
                select(DeviceState).where(
                    and_(
                        DeviceState.device_type == device_type.value,
                        DeviceState.device_id == controller_id
                    )
                )
            )
            device = existing.scalar_one_or_none()
            
            if not device:
                device = DeviceState(
                    device_type=device_type.value,
                    device_id=controller_id,
                    status="off",
                    auto_mode=True
                )
                self.session.add(device)
            
            devices.append(device)
        
        await self.session.commit()
        return devices

    async def is_controller_registered(self, controller_id: str) -> bool:
        """Проверка, зарегистрирован ли контроллер"""
        result = await self.session.execute(
            select(DeviceState).where(DeviceState.device_id == controller_id).limit(1)
        )
        return result.scalar_one_or_none() is not None
