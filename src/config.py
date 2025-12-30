"""
Конфигурация для умной теплицы с клубникой.
Оптимальные параметры для выращивания клубники.
"""
import os
from pydantic_settings import BaseSettings


class StrawberryConfig(BaseSettings):
    """Оптимальные параметры для выращивания клубники"""
    
    # Температура воздуха (°C)
    TEMP_DAY_MIN: float = 18.0
    TEMP_DAY_MAX: float = 25.0
    TEMP_NIGHT_MIN: float = 15.0
    TEMP_NIGHT_MAX: float = 18.0
    TEMP_CRITICAL_LOW: float = 5.0
    TEMP_CRITICAL_HIGH: float = 35.0
    
    # Влажность воздуха (%)
    HUMIDITY_MIN: float = 60.0
    HUMIDITY_MAX: float = 75.0
    HUMIDITY_CRITICAL_LOW: float = 40.0
    HUMIDITY_CRITICAL_HIGH: float = 90.0
    
    # Влажность почвы (%)
    SOIL_MOISTURE_MIN: float = 60.0
    SOIL_MOISTURE_MAX: float = 80.0
    SOIL_MOISTURE_CRITICAL_LOW: float = 40.0
    SOIL_MOISTURE_CRITICAL_HIGH: float = 95.0
    
    # Освещение
    LIGHT_HOURS_MIN: int = 12
    LIGHT_HOURS_MAX: int = 16
    LIGHT_INTENSITY_MIN: int = 200  # люкс
    LIGHT_INTENSITY_MAX: int = 600  # люкс
    
    # pH почвы
    PH_MIN: float = 5.5
    PH_MAX: float = 6.8
    
    # Время дня/ночи (часы)
    DAY_START_HOUR: int = 6
    DAY_END_HOUR: int = 22


class ServerConfig(BaseSettings):
    """Конфигурация сервера"""
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "greenhouse"
    POSTGRES_PASSWORD: str = "greenhouse"
    POSTGRES_DB: str = "greenhouse"
    
    # SQLite fallback for local development
    USE_SQLITE: bool = False
    
    SECRET_KEY: str = "strawberry-greenhouse-secret-key-2024"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Интервалы опроса (секунды)
    SENSOR_READ_INTERVAL: int = 60
    CONTROL_CHECK_INTERVAL: int = 30
    
    @property
    def DATABASE_URL(self) -> str:
        """Формирование URL базы данных"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    class Config:
        env_file = ".env"


# Глобальные экземпляры конфигурации
strawberry_config = StrawberryConfig()
server_config = ServerConfig()
