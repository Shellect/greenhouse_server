/*
 * 🍓 Strawberry Greenhouse Controller
 * NodeMCU ESP8266 firmware for smart greenhouse
 * 
 * Датчики:
 * - DHT22: температура и влажность воздуха
 * - Soil Moisture Sensor: влажность почвы
 * - BH1750: освещённость
 * - (опционально) pH sensor
 * 
 * Устройства управления:
 * - Relay 1: Насос полива
 * - Relay 2: Вентилятор
 * - Relay 3: Обогреватель
 * - Relay 4: Освещение
 * 
 * Подключение к серверу по WiFi через HTTP API
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ==================== КОНФИГУРАЦИЯ ====================

// WiFi настройки
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Сервер теплицы
const char* SERVER_HOST = "192.168.1.100";  // IP вашего сервера
const int SERVER_PORT = 8000;
const char* DEVICE_ID = "nodemcu-1";

// ==================== ПИНЫ ====================

// Датчики
#define DHT_PIN D4           // DHT22 data pin
#define DHT_TYPE DHT22
#define SOIL_MOISTURE_PIN A0 // Аналоговый вход для датчика влажности почвы

// Реле (активный низкий уровень)
#define RELAY_PUMP D1        // Насос полива
#define RELAY_FAN D2         // Вентилятор
#define RELAY_HEATER D5      // Обогреватель
#define RELAY_LIGHT D6       // Освещение
#define RELAY_HUMIDIFIER D7  // Увлажнитель
#define RELAY_COOLER D8      // Охладитель

// Индикатор
#define LED_PIN LED_BUILTIN

// ==================== ИНТЕРВАЛЫ ====================

const unsigned long SENSOR_READ_INTERVAL = 30000;   // 30 секунд
const unsigned long SERVER_SEND_INTERVAL = 60000;   // 1 минута
const unsigned long COMMAND_CHECK_INTERVAL = 10000; // 10 секунд

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient wifiClient;

// Последние показания датчиков
float lastTemperature = 0;
float lastHumidity = 0;
float lastSoilMoisture = 0;
float lastLightLevel = 0;

// Состояние устройств
bool pumpOn = false;
bool fanOn = false;
bool heaterOn = false;
bool lightOn = false;
bool humidifierOn = false;
bool coolerOn = false;

// Таймеры
unsigned long lastSensorRead = 0;
unsigned long lastServerSend = 0;
unsigned long lastCommandCheck = 0;

// Таймеры автоотключения устройств
unsigned long pumpStartTime = 0;
unsigned long pumpDuration = 0;

// ==================== SETUP ====================

void setup() {
    Serial.begin(115200);
    Serial.println("\n\n🍓 Strawberry Greenhouse Controller Starting...");
    
    // Инициализация пинов реле
    pinMode(RELAY_PUMP, OUTPUT);
    pinMode(RELAY_FAN, OUTPUT);
    pinMode(RELAY_HEATER, OUTPUT);
    pinMode(RELAY_LIGHT, OUTPUT);
    pinMode(RELAY_HUMIDIFIER, OUTPUT);
    pinMode(RELAY_COOLER, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    
    // Выключаем все реле (HIGH = выкл для активных низких реле)
    digitalWrite(RELAY_PUMP, HIGH);
    digitalWrite(RELAY_FAN, HIGH);
    digitalWrite(RELAY_HEATER, HIGH);
    digitalWrite(RELAY_LIGHT, HIGH);
    digitalWrite(RELAY_HUMIDIFIER, HIGH);
    digitalWrite(RELAY_COOLER, HIGH);
    
    // Инициализация DHT
    dht.begin();
    
    // Подключение к WiFi
    connectWiFi();
    
    Serial.println("✅ Setup complete!");
}

// ==================== MAIN LOOP ====================

void loop() {
    unsigned long currentMillis = millis();
    
    // Проверяем WiFi подключение
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }
    
    // Чтение датчиков
    if (currentMillis - lastSensorRead >= SENSOR_READ_INTERVAL) {
        readSensors();
        lastSensorRead = currentMillis;
    }
    
    // Отправка данных на сервер
    if (currentMillis - lastServerSend >= SERVER_SEND_INTERVAL) {
        sendDataToServer();
        lastServerSend = currentMillis;
    }
    
    // Проверка команд с сервера
    if (currentMillis - lastCommandCheck >= COMMAND_CHECK_INTERVAL) {
        checkServerCommands();
        lastCommandCheck = currentMillis;
    }
    
    // Проверка таймеров устройств
    checkDeviceTimers();
    
    // Мигаем LED для индикации работы
    digitalWrite(LED_PIN, (millis() / 1000) % 2);
    
    delay(100);
}

// ==================== WIFI ====================

void connectWiFi() {
    Serial.print("📶 Connecting to WiFi: ");
    Serial.println(WIFI_SSID);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi connection failed!");
    }
}

// ==================== SENSORS ====================

void readSensors() {
    Serial.println("\n📊 Reading sensors...");
    
    // DHT22: температура и влажность
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    
    if (!isnan(temp)) {
        lastTemperature = temp;
        Serial.print("🌡️ Temperature: ");
        Serial.print(lastTemperature);
        Serial.println("°C");
    }
    
    if (!isnan(hum)) {
        lastHumidity = hum;
        Serial.print("💨 Humidity: ");
        Serial.print(lastHumidity);
        Serial.println("%");
    }
    
    // Влажность почвы (аналоговый датчик)
    int soilRaw = analogRead(SOIL_MOISTURE_PIN);
    // Конвертируем в проценты (калибровка может потребоваться)
    // Типично: сухая почва = 1024, мокрая = 300
    lastSoilMoisture = map(soilRaw, 1024, 300, 0, 100);
    lastSoilMoisture = constrain(lastSoilMoisture, 0, 100);
    
    Serial.print("🌱 Soil moisture: ");
    Serial.print(lastSoilMoisture);
    Serial.print("% (raw: ");
    Serial.print(soilRaw);
    Serial.println(")");
    
    // Освещённость (если подключен датчик BH1750 по I2C)
    // Для простоты используем фоторезистор на A0 (нужен мультиплексор)
    // или отдельный аналоговый пин
    // lastLightLevel = readLightSensor();
    lastLightLevel = 400; // Заглушка, замените реальным чтением
    
    Serial.print("☀️ Light level: ");
    Serial.print(lastLightLevel);
    Serial.println(" lux");
}

// ==================== SERVER COMMUNICATION ====================

void sendDataToServer() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("❌ WiFi not connected, skipping data send");
        return;
    }
    
    Serial.println("\n📤 Sending data to server...");
    
    HTTPClient http;
    String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/v1/sensors/data";
    
    http.begin(wifiClient, url);
    http.addHeader("Content-Type", "application/json");
    
    // Формируем JSON
    StaticJsonDocument<256> doc;
    doc["temperature"] = lastTemperature;
    doc["humidity"] = lastHumidity;
    doc["soil_moisture"] = lastSoilMoisture;
    doc["light_level"] = lastLightLevel;
    doc["device_id"] = DEVICE_ID;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    Serial.print("Sending: ");
    Serial.println(jsonString);
    
    int httpCode = http.POST(jsonString);
    
    if (httpCode > 0) {
        Serial.print("Response code: ");
        Serial.println(httpCode);
        
        if (httpCode == HTTP_CODE_OK) {
            String response = http.getString();
            Serial.print("Response: ");
            Serial.println(response);
            
            // Парсим команды из ответа
            parseServerResponse(response);
        }
    } else {
        Serial.print("❌ HTTP error: ");
        Serial.println(http.errorToString(httpCode));
    }
    
    http.end();
}

void parseServerResponse(String response) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (error) {
        Serial.print("❌ JSON parse error: ");
        Serial.println(error.c_str());
        return;
    }
    
    // Обрабатываем команды
    JsonArray commands = doc["commands"];
    for (JsonObject cmd : commands) {
        const char* device = cmd["device"];
        const char* action = cmd["action"];
        int duration = cmd["duration"] | 0;
        
        executeCommand(device, action, duration);
    }
    
    // Показываем health score
    float healthScore = doc["health_score"] | 0;
    Serial.print("🏥 Health score: ");
    Serial.println(healthScore);
}

void checkServerCommands() {
    if (WiFi.status() != WL_CONNECTED) {
        return;
    }
    
    HTTPClient http;
    String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/v1/devices/commands/pending";
    
    http.begin(wifiClient, url);
    int httpCode = http.GET();
    
    if (httpCode == HTTP_CODE_OK) {
        String response = http.getString();
        
        StaticJsonDocument<1024> doc;
        DeserializationError error = deserializeJson(doc, response);
        
        if (!error) {
            JsonArray commands = doc["commands"];
            for (JsonObject cmd : commands) {
                const char* device = cmd["device"];
                const char* action = cmd["action"];
                bool autoMode = cmd["auto_mode"] | true;
                
                // Выполняем только если устройство в нужном состоянии
                executeCommand(device, action, 0);
            }
        }
    }
    
    http.end();
}

// ==================== DEVICE CONTROL ====================

void executeCommand(const char* device, const char* action, int duration) {
    bool turnOn = (strcmp(action, "on") == 0);
    
    Serial.print("⚡ Command: ");
    Serial.print(device);
    Serial.print(" -> ");
    Serial.println(action);
    
    if (strcmp(device, "pump") == 0) {
        setPump(turnOn);
        if (turnOn && duration > 0) {
            pumpStartTime = millis();
            pumpDuration = duration * 1000;
        }
    }
    else if (strcmp(device, "fan") == 0) {
        setFan(turnOn);
    }
    else if (strcmp(device, "heater") == 0) {
        setHeater(turnOn);
    }
    else if (strcmp(device, "light") == 0) {
        setLight(turnOn);
    }
    else if (strcmp(device, "humidifier") == 0) {
        setHumidifier(turnOn);
    }
    else if (strcmp(device, "cooler") == 0) {
        setCooler(turnOn);
    }
}

void setPump(bool on) {
    pumpOn = on;
    digitalWrite(RELAY_PUMP, on ? LOW : HIGH);
    Serial.print("💧 Pump: ");
    Serial.println(on ? "ON" : "OFF");
}

void setFan(bool on) {
    fanOn = on;
    digitalWrite(RELAY_FAN, on ? LOW : HIGH);
    Serial.print("🌀 Fan: ");
    Serial.println(on ? "ON" : "OFF");
}

void setHeater(bool on) {
    heaterOn = on;
    digitalWrite(RELAY_HEATER, on ? LOW : HIGH);
    Serial.print("🔥 Heater: ");
    Serial.println(on ? "ON" : "OFF");
}

void setLight(bool on) {
    lightOn = on;
    digitalWrite(RELAY_LIGHT, on ? LOW : HIGH);
    Serial.print("💡 Light: ");
    Serial.println(on ? "ON" : "OFF");
}

void setHumidifier(bool on) {
    humidifierOn = on;
    digitalWrite(RELAY_HUMIDIFIER, on ? LOW : HIGH);
    Serial.print("🌫️ Humidifier: ");
    Serial.println(on ? "ON" : "OFF");
}

void setCooler(bool on) {
    coolerOn = on;
    digitalWrite(RELAY_COOLER, on ? LOW : HIGH);
    Serial.print("❄️ Cooler: ");
    Serial.println(on ? "ON" : "OFF");
}

// ==================== DEVICE TIMERS ====================

void checkDeviceTimers() {
    // Автоотключение насоса по таймеру
    if (pumpOn && pumpDuration > 0) {
        if (millis() - pumpStartTime >= pumpDuration) {
            setPump(false);
            pumpDuration = 0;
            Serial.println("⏱️ Pump auto-off by timer");
        }
    }
}

// ==================== UTILITY FUNCTIONS ====================

// Калибровка датчика влажности почвы
// Замените значения на реальные для вашего датчика
const int SOIL_DRY = 1024;    // Значение при сухой почве
const int SOIL_WET = 300;     // Значение при мокрой почве

float calibrateSoilMoisture(int rawValue) {
    float percentage = map(rawValue, SOIL_DRY, SOIL_WET, 0, 100);
    return constrain(percentage, 0, 100);
}



