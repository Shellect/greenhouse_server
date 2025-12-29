"""
Greenhouse Smart Server - Сервер умной теплицы для клубники.
Главный файл приложения FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.sensors import sensors_router
from src.routers.devices import devices_router
from src.routers.alerts import alerts_router
from src.routers.control import control_router
from src.routers.growth import growth_router


app = FastAPI(
    title="🍓 Strawberry Greenhouse API",
    description="API для умной теплицы с клубникой на базе NodeMCU",
    version="1.0.0"
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
app.include_router(sensors_router, prefix='/api/v1')
app.include_router(devices_router, prefix='/api/v1')
app.include_router(alerts_router, prefix='/api/v1')
app.include_router(control_router, prefix='/api/v1')
app.include_router(growth_router, prefix='/api/v1')
