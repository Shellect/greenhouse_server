"""
Роутер для логов роста растений.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.controller import greenhouse_controller
from src.database import get_session
from src.models import GrowthStage
from src.repositories import GrowthRepository

growth_router = APIRouter(prefix="/growth", tags=["Growth"])


@growth_router.post("/log")
async def create_growth_log(
    stage: GrowthStage,
    notes: Optional[str] = None,
    photo_url: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Добавление записи в лог роста"""
    growth_repo = GrowthRepository(db)
    log = await growth_repo.add(stage.value, notes, photo_url)
    greenhouse_controller.set_growth_stage(stage)
    return {"status": "ok", "log_id": log.id, "stage": stage.value}


@growth_router.get("/logs")
async def list_growth_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session)
):
    """Получение логов роста"""
    growth_repo = GrowthRepository(db)
    logs = await growth_repo.get_all(limit=limit)
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "stage": log.stage,
                "notes": log.notes,
                "photo_url": log.photo_url
            }
            for log in logs
        ]
    }
