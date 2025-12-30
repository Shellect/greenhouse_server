"""
Greenhouse Smart Server - Сервер умной теплицы для клубники.
Главный файл приложения FastAPI.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import strawberry_config
from database import init_db
from routers.sensors import sensors_router
from routers.devices import devices_router
from routers.alerts import alerts_router
from routers.control import control_router
from routers.growth import growth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    await init_db()
    print("🌱 Greenhouse Server started!")
    print(f"🍓 Strawberry optimal temp: {strawberry_config.TEMP_DAY_MIN}-{strawberry_config.TEMP_DAY_MAX}°C")
    yield
    print("🌙 Greenhouse Server shutting down...")


app = FastAPI(
    title="🍓 Strawberry Greenhouse API",
    description="API для умной теплицы с клубникой на базе NodeMCU",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для доступа с NodeMCU и веб-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Подключение роутеров ====================
# Sensors
app.include_router(sensors_router, prefix='/api/v1')

# Devices
app.include_router(devices_router, prefix='/api/v1')

# Alerts
app.include_router(alerts_router, prefix='/api/v1')

# Status & Control
app.include_router(control_router, prefix='/api/v1')

# Growth
app.include_router(growth_router, prefix='/api/v1')

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
