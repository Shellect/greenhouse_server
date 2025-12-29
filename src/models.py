"""
Модели данных для умной теплицы.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ==================== Enums ====================

class DeviceType(str, Enum):
    """Типы устройств"""
    PUMP = "pump"                    # Насос полива
    FAN = "fan"                      # Вентилятор
    HEATER = "heater"                # Обогреватель
    COOLER = "cooler"                # Охладитель
    LIGHT = "light"                  # Освещение
    HUMIDIFIER = "humidifier"        # Увлажнитель
    DEHUMIDIFIER = "dehumidifier"    # Осушитель


class DeviceStatus(str, Enum):
    """Статус устройства"""
    ON = "on"
    OFF = "off"
    ERROR = "error"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Уровень оповещения"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class GrowthStage(str, Enum):
    """Стадия роста клубники"""
    SEEDLING = "seedling"           # Рассада
    VEGETATIVE = "vegetative"       # Вегетативный рост
    FLOWERING = "flowering"         # Цветение
    FRUITING = "fruiting"           # Плодоношение
    DORMANT = "dormant"             # Покой


# ==================== SQLAlchemy Models ====================

class SensorReading(Base):
    """Показания датчиков"""
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Температура
    temperature = Column(Float, nullable=True)
    
    # Влажность воздуха
    humidity = Column(Float, nullable=True)
    
    # Влажность почвы
    soil_moisture = Column(Float, nullable=True)
    
    # Освещённость (люкс)
    light_level = Column(Float, nullable=True)
    
    # pH почвы
    ph_level = Column(Float, nullable=True)
    
    # CO2 (ppm)
    co2_level = Column(Float, nullable=True)
    
    # ID устройства NodeMCU
    device_id = Column(String(50), default="nodemcu-1")


class DeviceState(Base):
    """Состояние устройств"""
    __tablename__ = "device_states"
    
    id = Column(Integer, primary_key=True, index=True)
    device_type = Column(String(50), index=True)
    device_id = Column(String(50), index=True)
    status = Column(String(20), default="off")
    last_updated = Column(DateTime, default=datetime.utcnow)
    auto_mode = Column(Boolean, default=True)


class Alert(Base):
    """Оповещения системы"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20))
    message = Column(String(500))
    parameter = Column(String(50))
    value = Column(Float, nullable=True)
    acknowledged = Column(Boolean, default=False)


class GrowthLog(Base):
    """Лог роста растений"""
    __tablename__ = "growth_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stage = Column(String(50))
    notes = Column(String(1000), nullable=True)
    photo_url = Column(String(500), nullable=True)


# ==================== Pydantic Schemas ====================

class SensorData(BaseModel):
    """Схема для приёма данных с датчиков"""
    temperature: Optional[float] = Field(None, description="Температура воздуха (°C)")
    humidity: Optional[float] = Field(None, description="Влажность воздуха (%)")
    soil_moisture: Optional[float] = Field(None, description="Влажность почвы (%)")
    light_level: Optional[float] = Field(None, description="Освещённость (люкс)")
    ph_level: Optional[float] = Field(None, description="pH почвы")
    co2_level: Optional[float] = Field(None, description="Уровень CO2 (ppm)")
    device_id: str = Field(default="nodemcu-1", description="ID устройства")
    
    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 22.5,
                "humidity": 65.0,
                "soil_moisture": 70.0,
                "light_level": 400,
                "device_id": "nodemcu-1"
            }
        }


class SensorDataResponse(SensorData):
    """Ответ с данными датчиков"""
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


class DeviceCommand(BaseModel):
    """Команда для устройства"""
    device_type: DeviceType
    device_id: str = "main"
    action: DeviceStatus
    duration: Optional[int] = Field(None, description="Длительность в секундах")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_type": "pump",
                "device_id": "main",
                "action": "on",
                "duration": 60
            }
        }


class DeviceStateResponse(BaseModel):
    """Состояние устройства"""
    device_type: str
    device_id: str
    status: str
    auto_mode: bool
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ConnectionStatus(BaseModel):
    """Статус подключения устройств"""
    device_connected: bool = Field(description="Есть ли подключённое устройство")
    last_reading_time: Optional[datetime] = Field(None, description="Время последнего чтения")
    seconds_since_last_reading: Optional[int] = Field(None, description="Секунд с последнего чтения")
    connection_quality: str = Field(default="unknown", description="Качество связи: good/weak/lost/unknown")


class GreenhouseStatus(BaseModel):
    """Общий статус теплицы"""
    connection: ConnectionStatus
    current_readings: Optional[SensorData]
    devices: List[DeviceStateResponse]
    active_alerts: int
    growth_stage: str
    health_score: float = Field(description="Оценка здоровья растений 0-100")
    recommendations: List[str]


class AlertCreate(BaseModel):
    """Создание оповещения"""
    level: AlertLevel
    message: str
    parameter: Optional[str] = None
    value: Optional[float] = None


class AlertResponse(BaseModel):
    """Ответ с оповещением"""
    id: int
    timestamp: datetime
    level: str
    message: str
    parameter: Optional[str]
    value: Optional[float]
    acknowledged: bool
    
    class Config:
        from_attributes = True


class ControlSettings(BaseModel):
    """Настройки автоматического контроля"""
    auto_watering: bool = True
    auto_ventilation: bool = True
    auto_heating: bool = True
    auto_lighting: bool = True
    growth_stage: GrowthStage = GrowthStage.VEGETATIVE


class CommandQueue(BaseModel):
    """Очередь команд для NodeMCU"""
    commands: List[DeviceCommand]
    timestamp: datetime = Field(default_factory=datetime.utcnow)



