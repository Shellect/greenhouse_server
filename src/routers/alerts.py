"""
Роутер для работы с оповещениями теплицы.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, get_active_alerts, acknowledge_alert
from models import AlertResponse

alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts_router.get("", response_model=List[AlertResponse])
async def list_alerts(
        limit: int = Query(default=50, ge=1, le=200),
        db: AsyncSession = Depends(get_session)
):
    """Получение списка активных оповещений"""
    return await get_active_alerts(db, limit=limit)


@alerts_router.post("/{alert_id}/acknowledge")
async def ack_alert(alert_id: int, db: AsyncSession = Depends(get_session)):
    """Подтверждение (закрытие) оповещения"""
    alert = await acknowledge_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "ok", "alert_id": alert_id}


