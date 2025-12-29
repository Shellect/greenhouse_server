"""
Alembic environment configuration.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Импортируем наши модели и конфигурацию
from src.config import server_config
from src.models import Base

# Alembic Config object
config = context.config

# Устанавливаем URL из нашего конфига (синхронный драйвер для Alembic)
config.set_main_option("sqlalchemy.url", server_config.DATABASE_URL_SYNC)

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные моделей для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Запуск миграций в offline-режиме.
    Генерирует SQL без подключения к БД.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Запуск миграций в online-режиме.
    Подключается к БД и применяет миграции.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Отслеживать изменения типов колонок
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
