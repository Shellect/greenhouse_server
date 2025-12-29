"""
Роутер для работы с оповещениями.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import AlertCreate, AlertResponse
from src.repositories import AlertRepository

alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts_router.get("", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session)
):
    """Получение активных оповещений"""
    alert_repo = AlertRepository(db)
    alerts = await alert_repo.get_active(limit=limit)
    return alerts


@alerts_router.post("", response_model=AlertResponse)
async def create_alert(
    alert: AlertCreate,
    db: AsyncSession = Depends(get_session)
):
    """Создание нового оповещения"""
    alert_repo = AlertRepository(db)
    new_alert = await alert_repo.create(
        level=alert.level.value,
        message=alert.message,
        parameter=alert.parameter,
        value=alert.value
    )
    return new_alert


@alerts_router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_session)
):
    """Подтверждение (закрытие) оповещения"""
    alert_repo = AlertRepository(db)
    alert = await alert_repo.acknowledge(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "status": "ok",
        "alert_id": alert_id,
        "message": "Alert acknowledged"
    }


@alerts_router.get("/count")
async def get_alerts_count(db: AsyncSession = Depends(get_session)):
    """Получение количества активных оповещений"""
    alert_repo = AlertRepository(db)
    count = await alert_repo.count_active()
    return {"active_alerts": count}
