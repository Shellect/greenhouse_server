"""
Конфигурация для умной теплицы с клубникой.
Оптимальные параметры для выращивания клубники.
"""
import logging
import secrets
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StrawberryConfig(BaseSettings):
    """Оптимальные параметры для выращивания клубники"""

    model_config = SettingsConfigDict(
        env_prefix="STRAWBERRY_",
        env_file=".env",
        extra="ignore"
    )

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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # Database (обязательные в production)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "greenhouse"
    POSTGRES_PASSWORD: str = "greenhouse"
    POSTGRES_DB: str = "greenhouse"

    # Security
    SECRET_KEY: Optional[str] = None  # Генерируется автоматически если не задан

    # API
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"

    # Интервалы опроса (секунды)
    SENSOR_READ_INTERVAL: int = 60
    CONTROL_CHECK_INTERVAL: int = 30

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def generate_secret_key(cls, v: Optional[str]) -> str:
        """Генерирует SECRET_KEY если не задан"""
        if v is None or v == "":
            generated = secrets.token_urlsafe(32)
            logging.warning(
                "⚠️  SECRET_KEY не задан, сгенерирован временный ключ. "
                "Для production задайте SECRET_KEY в переменных окружения!"
            )
            return generated
        return v

    @property
    def DATABASE_URL(self) -> str:
        """URL для asyncpg (асинхронный драйвер)"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """URL для psycopg2 (синхронный драйвер, для Alembic)"""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# Глобальные экземпляры конфигурации
strawberry_config = StrawberryConfig()
server_config = ServerConfig()

# Настройка логирования для SQLAlchemy и драйверов БД
_db_log_level = getattr(logging, server_config.LOG_LEVEL.upper(), logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(_db_log_level)
logging.getLogger("sqlalchemy.pool").setLevel(_db_log_level)
logging.getLogger("sqlalchemy.dialects").setLevel(_db_log_level)
logging.getLogger("asyncpg").setLevel(_db_log_level)
logging.getLogger("aiosqlite").setLevel(_db_log_level)
