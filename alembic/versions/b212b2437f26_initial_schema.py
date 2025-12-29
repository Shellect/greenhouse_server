"""initial_schema

Revision ID: b212b2437f26
Revises: 
Create Date: 2024-12-29

Начальная схема базы данных для умной теплицы.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b212b2437f26'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица показаний датчиков
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('soil_moisture', sa.Float(), nullable=True),
        sa.Column('light_level', sa.Float(), nullable=True),
        sa.Column('ph_level', sa.Float(), nullable=True),
        sa.Column('co2_level', sa.Float(), nullable=True),
        sa.Column('device_id', sa.String(50), default='nodemcu-1'),
    )

    # Таблица состояния устройств
    op.create_table(
        'device_states',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('device_type', sa.String(50), index=True),
        sa.Column('device_id', sa.String(50), index=True),
        sa.Column('status', sa.String(20), default='off'),
        sa.Column('last_updated', sa.DateTime(), default=sa.func.now()),
        sa.Column('auto_mode', sa.Boolean(), default=True),
    )

    # Таблица оповещений
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('level', sa.String(20)),
        sa.Column('message', sa.String(500)),
        sa.Column('parameter', sa.String(50), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), default=False),
    )

    # Таблица логов роста
    op.create_table(
        'growth_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
        sa.Column('stage', sa.String(50)),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('growth_logs')
    op.drop_table('alerts')
    op.drop_table('device_states')
    op.drop_table('sensor_readings')
