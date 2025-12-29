"""
Контроллер автоматизации теплицы.
Анализирует показания датчиков и принимает решения об управлении.
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from src.models import DeviceType, DeviceStatus, AlertLevel, GrowthStage, DeviceCommand
from src.config import strawberry_config as cfg


class GreenhouseController:
    """Контроллер умной теплицы для клубники"""
    
    def __init__(self):
        self.current_stage = GrowthStage.VEGETATIVE
        self.pending_commands: List[DeviceCommand] = []
        self.last_watering: Optional[datetime] = None
        self.watering_cooldown_minutes = 30  # Минимальный интервал полива
        
    def set_growth_stage(self, stage: GrowthStage):
        """Установка стадии роста"""
        self.current_stage = stage
        
    def is_daytime(self) -> bool:
        """Проверка: сейчас день или ночь"""
        hour = datetime.now().hour
        return cfg.DAY_START_HOUR <= hour < cfg.DAY_END_HOUR
    
    def get_target_temperature(self) -> Tuple[float, float]:
        """Получение целевой температуры в зависимости от времени суток"""
        if self.is_daytime():
            return cfg.TEMP_DAY_MIN, cfg.TEMP_DAY_MAX
        return cfg.TEMP_NIGHT_MIN, cfg.TEMP_NIGHT_MAX
    
    def analyze_readings(self, readings: dict) -> Dict:
        """
        Анализ показаний датчиков и генерация команд/оповещений.
        
        Args:
            readings: словарь с показаниями датчиков
            
        Returns:
            dict с командами, оповещениями и рекомендациями
        """
        commands = []
        alerts = []
        recommendations = []
        health_score = 100.0
        
        # Анализ температуры
        temp_result = self._analyze_temperature(readings.get("temperature"))
        commands.extend(temp_result["commands"])
        alerts.extend(temp_result["alerts"])
        recommendations.extend(temp_result["recommendations"])
        health_score -= temp_result["penalty"]
        
        # Анализ влажности воздуха
        humidity_result = self._analyze_humidity(readings.get("humidity"))
        commands.extend(humidity_result["commands"])
        alerts.extend(humidity_result["alerts"])
        recommendations.extend(humidity_result["recommendations"])
        health_score -= humidity_result["penalty"]
        
        # Анализ влажности почвы
        soil_result = self._analyze_soil_moisture(readings.get("soil_moisture"))
        commands.extend(soil_result["commands"])
        alerts.extend(soil_result["alerts"])
        recommendations.extend(soil_result["recommendations"])
        health_score -= soil_result["penalty"]
        
        # Анализ освещения
        light_result = self._analyze_light(readings.get("light_level"))
        commands.extend(light_result["commands"])
        alerts.extend(light_result["alerts"])
        recommendations.extend(light_result["recommendations"])
        health_score -= light_result["penalty"]
        
        # Анализ pH
        ph_result = self._analyze_ph(readings.get("ph_level"))
        alerts.extend(ph_result["alerts"])
        recommendations.extend(ph_result["recommendations"])
        health_score -= ph_result["penalty"]
        
        return {
            "commands": commands,
            "alerts": alerts,
            "recommendations": recommendations,
            "health_score": max(0, min(100, health_score)),
            "is_daytime": self.is_daytime(),
            "growth_stage": self.current_stage.value
        }
    
    def _analyze_temperature(self, temp: Optional[float]) -> Dict:
        """Анализ температуры"""
        result = {"commands": [], "alerts": [], "recommendations": [], "penalty": 0}
        
        if temp is None:
            result["recommendations"].append("⚠️ Нет данных о температуре")
            return result
        
        target_min, target_max = self.get_target_temperature()
        period = "дня" if self.is_daytime() else "ночи"
        
        # Критически низкая температура
        if temp < cfg.TEMP_CRITICAL_LOW:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"🚨 КРИТИЧЕСКИ низкая температура: {temp}°C! Риск гибели растений!",
                "parameter": "temperature",
                "value": temp
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HEATER,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 40
            
        # Критически высокая температура
        elif temp > cfg.TEMP_CRITICAL_HIGH:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"🚨 КРИТИЧЕСКИ высокая температура: {temp}°C! Срочно охладить!",
                "parameter": "temperature",
                "value": temp
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.COOLER,
                action=DeviceStatus.ON
            ))
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.FAN,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 40
            
        # Ниже нормы
        elif temp < target_min:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"🌡️ Температура ниже нормы для {period}: {temp}°C (норма: {target_min}-{target_max}°C)",
                "parameter": "temperature",
                "value": temp
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HEATER,
                action=DeviceStatus.ON
            ))
            result["recommendations"].append(f"Включить обогрев до достижения {target_min}°C")
            result["penalty"] = 15
            
        # Выше нормы
        elif temp > target_max:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"🌡️ Температура выше нормы для {period}: {temp}°C (норма: {target_min}-{target_max}°C)",
                "parameter": "temperature",
                "value": temp
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.FAN,
                action=DeviceStatus.ON
            ))
            result["recommendations"].append("Включить вентиляцию для охлаждения")
            result["penalty"] = 10
            
        # Норма - выключаем устройства
        else:
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HEATER,
                action=DeviceStatus.OFF
            ))
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.COOLER,
                action=DeviceStatus.OFF
            ))
        
        return result
    
    def _analyze_humidity(self, humidity: Optional[float]) -> Dict:
        """Анализ влажности воздуха"""
        result = {"commands": [], "alerts": [], "recommendations": [], "penalty": 0}
        
        if humidity is None:
            result["recommendations"].append("⚠️ Нет данных о влажности воздуха")
            return result
        
        if humidity < cfg.HUMIDITY_CRITICAL_LOW:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"💨 КРИТИЧЕСКИ низкая влажность воздуха: {humidity}%!",
                "parameter": "humidity",
                "value": humidity
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HUMIDIFIER,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 25
            
        elif humidity > cfg.HUMIDITY_CRITICAL_HIGH:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"💨 КРИТИЧЕСКИ высокая влажность: {humidity}%! Риск грибковых заболеваний!",
                "parameter": "humidity",
                "value": humidity
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.DEHUMIDIFIER,
                action=DeviceStatus.ON
            ))
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.FAN,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 30
            
        elif humidity < cfg.HUMIDITY_MIN:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"💧 Влажность воздуха ниже нормы: {humidity}% (норма: {cfg.HUMIDITY_MIN}-{cfg.HUMIDITY_MAX}%)",
                "parameter": "humidity",
                "value": humidity
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HUMIDIFIER,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 10
            
        elif humidity > cfg.HUMIDITY_MAX:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"💧 Влажность воздуха выше нормы: {humidity}% (норма: {cfg.HUMIDITY_MIN}-{cfg.HUMIDITY_MAX}%)",
                "parameter": "humidity",
                "value": humidity
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.FAN,
                action=DeviceStatus.ON
            ))
            result["penalty"] = 8
            
        else:
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.HUMIDIFIER,
                action=DeviceStatus.OFF
            ))
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.DEHUMIDIFIER,
                action=DeviceStatus.OFF
            ))
        
        return result
    
    def _analyze_soil_moisture(self, moisture: Optional[float]) -> Dict:
        """Анализ влажности почвы"""
        result = {"commands": [], "alerts": [], "recommendations": [], "penalty": 0}
        
        if moisture is None:
            result["recommendations"].append("⚠️ Нет данных о влажности почвы")
            return result
        
        # Проверяем cooldown полива
        can_water = True
        if self.last_watering:
            minutes_since = (datetime.now() - self.last_watering).total_seconds() / 60
            can_water = minutes_since >= self.watering_cooldown_minutes
        
        if moisture < cfg.SOIL_MOISTURE_CRITICAL_LOW:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"🏜️ КРИТИЧЕСКИ сухая почва: {moisture}%! Растения увядают!",
                "parameter": "soil_moisture",
                "value": moisture
            })
            if can_water:
                result["commands"].append(DeviceCommand(
                    device_type=DeviceType.PUMP,
                    action=DeviceStatus.ON,
                    duration=120  # 2 минуты интенсивного полива
                ))
                self.last_watering = datetime.now()
            result["penalty"] = 35
            
        elif moisture > cfg.SOIL_MOISTURE_CRITICAL_HIGH:
            result["alerts"].append({
                "level": AlertLevel.CRITICAL,
                "message": f"🌊 ПЕРЕУВЛАЖНЕНИЕ почвы: {moisture}%! Риск загнивания корней!",
                "parameter": "soil_moisture",
                "value": moisture
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.PUMP,
                action=DeviceStatus.OFF
            ))
            result["recommendations"].append("Прекратить полив, обеспечить дренаж")
            result["penalty"] = 30
            
        elif moisture < cfg.SOIL_MOISTURE_MIN:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"🌱 Почва подсыхает: {moisture}% (норма: {cfg.SOIL_MOISTURE_MIN}-{cfg.SOIL_MOISTURE_MAX}%)",
                "parameter": "soil_moisture",
                "value": moisture
            })
            if can_water:
                result["commands"].append(DeviceCommand(
                    device_type=DeviceType.PUMP,
                    action=DeviceStatus.ON,
                    duration=60  # 1 минута полива
                ))
                self.last_watering = datetime.now()
            result["penalty"] = 10
            
        elif moisture > cfg.SOIL_MOISTURE_MAX:
            result["alerts"].append({
                "level": AlertLevel.INFO,
                "message": f"💧 Почва достаточно влажная: {moisture}%",
                "parameter": "soil_moisture",
                "value": moisture
            })
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.PUMP,
                action=DeviceStatus.OFF
            ))
            
        else:
            # Норма - насос выключен
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.PUMP,
                action=DeviceStatus.OFF
            ))
        
        return result
    
    def _analyze_light(self, light_level: Optional[float]) -> Dict:
        """Анализ освещённости"""
        result = {"commands": [], "alerts": [], "recommendations": [], "penalty": 0}
        
        if light_level is None:
            result["recommendations"].append("⚠️ Нет данных об освещённости")
            return result
        
        # Определяем нужно ли искусственное освещение
        if self.is_daytime():
            if light_level < cfg.LIGHT_INTENSITY_MIN:
                result["alerts"].append({
                    "level": AlertLevel.WARNING,
                    "message": f"☁️ Недостаточное освещение: {light_level} люкс (норма: {cfg.LIGHT_INTENSITY_MIN}+ люкс)",
                    "parameter": "light_level",
                    "value": light_level
                })
                result["commands"].append(DeviceCommand(
                    device_type=DeviceType.LIGHT,
                    action=DeviceStatus.ON
                ))
                result["recommendations"].append("Включить дополнительное освещение")
                result["penalty"] = 10
                
            elif light_level > cfg.LIGHT_INTENSITY_MAX:
                result["alerts"].append({
                    "level": AlertLevel.INFO,
                    "message": f"☀️ Интенсивное освещение: {light_level} люкс",
                    "parameter": "light_level",
                    "value": light_level
                })
                result["commands"].append(DeviceCommand(
                    device_type=DeviceType.LIGHT,
                    action=DeviceStatus.OFF
                ))
                result["recommendations"].append("Достаточно естественного света")
                
            else:
                result["commands"].append(DeviceCommand(
                    device_type=DeviceType.LIGHT,
                    action=DeviceStatus.OFF
                ))
        else:
            # Ночью выключаем свет (если нет специального режима)
            result["commands"].append(DeviceCommand(
                device_type=DeviceType.LIGHT,
                action=DeviceStatus.OFF
            ))
        
        return result
    
    def _analyze_ph(self, ph: Optional[float]) -> Dict:
        """Анализ pH почвы"""
        result = {"commands": [], "alerts": [], "recommendations": [], "penalty": 0}
        
        if ph is None:
            return result
        
        if ph < cfg.PH_MIN:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"⚗️ pH почвы слишком низкий: {ph} (норма: {cfg.PH_MIN}-{cfg.PH_MAX})",
                "parameter": "ph_level",
                "value": ph
            })
            result["recommendations"].append("Добавить известь для повышения pH")
            result["penalty"] = 15
            
        elif ph > cfg.PH_MAX:
            result["alerts"].append({
                "level": AlertLevel.WARNING,
                "message": f"⚗️ pH почвы слишком высокий: {ph} (норма: {cfg.PH_MIN}-{cfg.PH_MAX})",
                "parameter": "ph_level",
                "value": ph
            })
            result["recommendations"].append("Добавить серу или торф для понижения pH")
            result["penalty"] = 15
        
        return result
    
    def get_stage_recommendations(self) -> List[str]:
        """Рекомендации по текущей стадии роста"""
        recommendations = {
            GrowthStage.SEEDLING: [
                "🌱 Стадия рассады: поддерживайте высокую влажность",
                "Температура 20-22°C оптимальна для укоренения",
                "Защищайте от прямых солнечных лучей"
            ],
            GrowthStage.VEGETATIVE: [
                "🌿 Вегетативный рост: обеспечьте достаточно азота",
                "Регулярный полив важен для развития листвы",
                "Удаляйте усы для укрепления куста"
            ],
            GrowthStage.FLOWERING: [
                "🌸 Цветение: ограничьте азот, добавьте калий",
                "Поддерживайте влажность воздуха 60-70%",
                "Обеспечьте опыление (встряхивание или вентилятор)"
            ],
            GrowthStage.FRUITING: [
                "🍓 Плодоношение: регулярный полив критичен",
                "Подкормка калием улучшит вкус ягод",
                "Собирайте спелые ягоды каждые 2-3 дня"
            ],
            GrowthStage.DORMANT: [
                "❄️ Период покоя: сократите полив",
                "Снизьте температуру до 5-10°C",
                "Минимальное освещение достаточно"
            ]
        }
        return recommendations.get(self.current_stage, [])


# Глобальный экземпляр контроллера
greenhouse_controller = GreenhouseController()



