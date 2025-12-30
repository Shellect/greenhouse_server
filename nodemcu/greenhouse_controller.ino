/*
 * 🍓 Strawberry Greenhouse Controller
 * NodeMCU ESP8266 firmware for smart greenhouse
 * 
 * Функции:
 * - WiFi provisioning через AP mode (без Serial)
 * - OLED дисплей для отображения статуса
 * - Настройки сохраняются в EEPROM
 * - QR код на корпусе содержит данные для подключения
 * - Web-сервер для приёма настроек с телефона
 * 
 * Датчики:
 * - DHT22: температура и влажность воздуха
 * - Soil Moisture Sensor: влажность почвы
 * - BH1750: освещённость (опционально)
 * 
 * Устройства управления:
 * - Relay 1-6: Насос, Вентилятор, Обогреватель, Освещение, Увлажнитель, Охладитель
 * 
 * Дисплей:
 * - OLED SSD1306 128x64 (I2C)
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <EEPROM.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <qrcode.h>  // QR Code generator

// ==================== КОНФИГУРАЦИЯ УСТРОЙСТВА ====================

// Уникальный идентификатор устройства (печатается на QR коде)
#define DEVICE_UID "GH-0001"

// AP настройки
#define AP_PASSWORD "greenhouse2024"

// ==================== OLED ДИСПЛЕЙ ====================

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1  // Не используется
#define OLED_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Экраны дисплея
enum DisplayScreen {
    SCREEN_BOOT,
    SCREEN_AP_MODE,
    SCREEN_QR_CODE,      // QR код для подключения
    SCREEN_CONNECTING,
    SCREEN_STATUS,
    SCREEN_SENSORS,
    SCREEN_DEVICES,
    SCREEN_ERROR
};

// QR Code buffer
QRCode qrcode;

DisplayScreen currentScreen = SCREEN_BOOT;
unsigned long lastScreenSwitch = 0;
const unsigned long SCREEN_SWITCH_INTERVAL = 5000; // 5 сек между экранами

// ==================== LED ИНДИКАЦИЯ ====================

#define LED_PIN LED_BUILTIN
#define LED_ON LOW
#define LED_OFF HIGH

// ==================== ПИНЫ ====================

// I2C для OLED (стандартные пины)
// SDA = D2 (GPIO4)
// SCL = D1 (GPIO5)

// Датчики
#define DHT_PIN D4
#define DHT_TYPE DHT22
#define SOIL_MOISTURE_PIN A0

// Реле (перенесены из-за I2C)
#define RELAY_PUMP D5        // Насос полива
#define RELAY_FAN D6         // Вентилятор
#define RELAY_HEATER D7      // Обогреватель
#define RELAY_LIGHT D8       // Освещение
#define RELAY_HUMIDIFIER D0  // Увлажнитель (GPIO16)
#define RELAY_COOLER D3      // Охладитель (осторожно - имеет pullup)

// Кнопка переключения экранов / сброса настроек
#define BUTTON_PIN D3  // Короткое нажатие = смена экрана, долгое (5с) = сброс

// ==================== EEPROM СТРУКТУРА ====================

#define EEPROM_SIZE 512

struct Config {
    uint16_t magic;
    char wifi_ssid[64];
    char wifi_password[64];
    char server_host[64];
    uint16_t server_port;
    char device_name[32];
    uint8_t checksum;
} config;

// ==================== СОСТОЯНИЯ УСТРОЙСТВА ====================

enum DeviceState {
    STATE_INIT,
    STATE_AP_MODE,
    STATE_CONNECTING,
    STATE_CONNECTION_FAILED,
    STATE_CONNECTED,
    STATE_WORKING
};

DeviceState currentState = STATE_INIT;
int connectionAttempts = 0;
const int MAX_CONNECTION_ATTEMPTS = 3;

// ==================== ИНТЕРВАЛЫ ====================

const unsigned long SENSOR_READ_INTERVAL = 30000;
const unsigned long SERVER_SEND_INTERVAL = 60000;
const unsigned long COMMAND_CHECK_INTERVAL = 10000;
const unsigned long DISPLAY_UPDATE_INTERVAL = 1000;
const unsigned long BUTTON_HOLD_TIME = 5000;

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================

ESP8266WebServer webServer(80);
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
unsigned long lastDisplayUpdate = 0;
unsigned long buttonPressTime = 0;
unsigned long lastLedToggle = 0;
bool ledState = false;

// Таймеры автоотключения
unsigned long pumpStartTime = 0;
unsigned long pumpDuration = 0;

// Статистика
unsigned long uptimeSeconds = 0;
int serverErrors = 0;
bool serverConnected = false;

// ==================== ПРОТОТИПЫ ФУНКЦИЙ ====================

void loadConfig();
void saveConfig();
void clearConfig();
uint8_t calculateChecksum();
bool isConfigValid();
void startAPMode();
void startStationMode();
void setupStatusServer();

// Web handlers
void handleRoot();
void handleScan();
void handleConfigure();
void handleStatus();
void handleReset();

// Display
void initDisplay();
void updateDisplay();
void drawBootScreen();
void drawAPModeScreen();
void drawQRCodeScreen();
void drawConnectingScreen();
void drawStatusScreen();
void drawSensorsScreen();
void drawDevicesScreen();
void drawErrorScreen(const char* error);
void drawProgressBar(int x, int y, int width, int height, int percent);
void drawWiFiIcon(int x, int y, int strength);
void generateAndDrawQR(const char* data);

// Other
void updateLED();
void readSensors();
void sendDataToServer();
void checkServerCommands();
void parseServerResponse(String response);
void executeCommand(const char* device, const char* action, int duration);
void checkButton();
void checkDeviceTimers();

// Управление реле
void setPump(bool on);
void setFan(bool on);
void setHeater(bool on);
void setLight(bool on);
void setHumidifier(bool on);
void setCooler(bool on);

// ==================== SETUP ====================

void setup() {
    // Инициализация пинов
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    
    pinMode(RELAY_PUMP, OUTPUT);
    pinMode(RELAY_FAN, OUTPUT);
    pinMode(RELAY_HEATER, OUTPUT);
    pinMode(RELAY_LIGHT, OUTPUT);
    pinMode(RELAY_HUMIDIFIER, OUTPUT);
    pinMode(RELAY_COOLER, OUTPUT);
    
    // Выключаем все реле
    digitalWrite(RELAY_PUMP, HIGH);
    digitalWrite(RELAY_FAN, HIGH);
    digitalWrite(RELAY_HEATER, HIGH);
    digitalWrite(RELAY_LIGHT, HIGH);
    digitalWrite(RELAY_HUMIDIFIER, HIGH);
    digitalWrite(RELAY_COOLER, HIGH);
    
    // Инициализация I2C и дисплея
    Wire.begin();
    initDisplay();
    
    // Показываем загрузочный экран
    drawBootScreen();
    delay(2000);
    
    // Инициализация EEPROM и DHT
    EEPROM.begin(EEPROM_SIZE);
    dht.begin();
    
    // Загружаем конфигурацию
    loadConfig();
    
    // Проверяем, удерживается ли кнопка при старте
    if (digitalRead(BUTTON_PIN) == LOW) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setCursor(0, 28);
        display.println(F("Hold 3s to reset..."));
        display.display();
        
        delay(3000);
        if (digitalRead(BUTTON_PIN) == LOW) {
            display.clearDisplay();
            display.setCursor(30, 28);
            display.println(F("RESETTING..."));
            display.display();
            delay(1000);
            clearConfig();
        }
    }
    
    // Решаем, в каком режиме запускаться
    if (isConfigValid()) {
        currentState = STATE_CONNECTING;
        currentScreen = SCREEN_CONNECTING;
        startStationMode();
    } else {
        currentState = STATE_AP_MODE;
        currentScreen = SCREEN_AP_MODE;
        startAPMode();
    }
}

// ==================== MAIN LOOP ====================

void loop() {
    unsigned long currentMillis = millis();
    
    // Обновляем uptime
    static unsigned long lastUptimeUpdate = 0;
    if (currentMillis - lastUptimeUpdate >= 1000) {
        uptimeSeconds++;
        lastUptimeUpdate = currentMillis;
    }
    
    // Обновляем LED индикацию
    updateLED();
    
    // Проверяем кнопку
    checkButton();
    
    // Обновляем дисплей
    if (currentMillis - lastDisplayUpdate >= DISPLAY_UPDATE_INTERVAL) {
        updateDisplay();
        lastDisplayUpdate = currentMillis;
    }
    
    // Обрабатываем состояния
    switch (currentState) {
        case STATE_AP_MODE:
            webServer.handleClient();
            
            // Автопереключение между AP_MODE и QR_CODE каждые 5 сек
            if (currentMillis - lastScreenSwitch >= SCREEN_SWITCH_INTERVAL) {
                if (currentScreen == SCREEN_AP_MODE) {
                    currentScreen = SCREEN_QR_CODE;
                } else {
                    currentScreen = SCREEN_AP_MODE;
                }
                lastScreenSwitch = currentMillis;
            }
            break;
            
        case STATE_CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                currentState = STATE_WORKING;
                currentScreen = SCREEN_STATUS;
                setupStatusServer();
            } else if (millis() - lastLedToggle > 15000) {
                connectionAttempts++;
                if (connectionAttempts >= MAX_CONNECTION_ATTEMPTS) {
                    currentState = STATE_CONNECTION_FAILED;
                    currentScreen = SCREEN_ERROR;
                } else {
                    WiFi.disconnect();
                    delay(100);
                    WiFi.begin(config.wifi_ssid, config.wifi_password);
                    lastLedToggle = millis();
                }
            }
            break;
            
        case STATE_CONNECTION_FAILED:
            // Показываем ошибку 5 секунд, затем в AP режим
            if (currentMillis - lastLedToggle > 5000) {
                startAPMode();
                currentState = STATE_AP_MODE;
                currentScreen = SCREEN_AP_MODE;
                connectionAttempts = 0;
            }
            break;
            
        case STATE_WORKING:
            webServer.handleClient();
            
            if (WiFi.status() != WL_CONNECTED) {
                currentState = STATE_CONNECTING;
                currentScreen = SCREEN_CONNECTING;
                connectionAttempts = 0;
                WiFi.begin(config.wifi_ssid, config.wifi_password);
                lastLedToggle = millis();
                break;
            }
            
            // Автопереключение экранов
            if (currentMillis - lastScreenSwitch >= SCREEN_SWITCH_INTERVAL) {
                if (currentScreen == SCREEN_STATUS) {
                    currentScreen = SCREEN_SENSORS;
                } else if (currentScreen == SCREEN_SENSORS) {
                    currentScreen = SCREEN_DEVICES;
                } else {
                    currentScreen = SCREEN_STATUS;
                }
                lastScreenSwitch = currentMillis;
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
            
            checkDeviceTimers();
            break;
    }
    
    delay(10);
}

// ==================== DISPLAY FUNCTIONS ====================

void initDisplay() {
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
        // Дисплей не найден - продолжаем без него
        return;
    }
    
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.cp437(true);
    display.display();
}

void updateDisplay() {
    display.clearDisplay();
    
    switch (currentScreen) {
        case SCREEN_BOOT:
            drawBootScreen();
            break;
        case SCREEN_AP_MODE:
            drawAPModeScreen();
            break;
        case SCREEN_QR_CODE:
            drawQRCodeScreen();
            break;
        case SCREEN_CONNECTING:
            drawConnectingScreen();
            break;
        case SCREEN_STATUS:
            drawStatusScreen();
            break;
        case SCREEN_SENSORS:
            drawSensorsScreen();
            break;
        case SCREEN_DEVICES:
            drawDevicesScreen();
            break;
        case SCREEN_ERROR:
            drawErrorScreen("Connection failed");
            break;
    }
    
    display.display();
}

void drawBootScreen() {
    display.clearDisplay();
    
    // Заголовок
    display.setTextSize(2);
    display.setCursor(10, 8);
    display.println(F("GREENHOUSE"));
    
    // Версия
    display.setTextSize(1);
    display.setCursor(35, 30);
    display.println(F("Controller"));
    
    // ID устройства
    display.setCursor(40, 45);
    display.println(DEVICE_UID);
    
    // Полоса загрузки
    display.drawRect(14, 55, 100, 6, SSD1306_WHITE);
    
    display.display();
}

void drawAPModeScreen() {
    // Заголовок
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("=== SETUP MODE ==="));
    
    // WiFi иконка (анимация)
    int phase = (millis() / 500) % 4;
    for (int i = 0; i < phase; i++) {
        display.drawCircle(118, 6, 2 + i * 3, SSD1306_WHITE);
    }
    
    display.setCursor(0, 14);
    display.println(F("Connect to WiFi:"));
    
    display.setTextSize(1);
    display.setCursor(0, 26);
    display.print(F("Greenhouse-"));
    display.println(DEVICE_UID);
    
    display.setCursor(0, 38);
    display.print(F("Pass: "));
    display.println(AP_PASSWORD);
    
    display.setCursor(0, 52);
    display.println(F("Press btn for QR"));
}

void drawQRCodeScreen() {
    // Генерируем данные для QR кода
    // Формат: GREENHOUSE:UID=GH-0001;SSID=Greenhouse-GH-0001;PWD=greenhouse2024
    String qrData = "GREENHOUSE:UID=";
    qrData += DEVICE_UID;
    qrData += ";SSID=Greenhouse-";
    qrData += DEVICE_UID;
    qrData += ";PWD=";
    qrData += AP_PASSWORD;
    
    generateAndDrawQR(qrData.c_str());
    
    // Подпись внизу
    display.setTextSize(1);
    display.setCursor(70, 20);
    display.println(F("Scan"));
    display.setCursor(70, 32);
    display.println(F("with"));
    display.setCursor(70, 44);
    display.println(F("app"));
}

void generateAndDrawQR(const char* data) {
    // QR Code Version 3 = 29x29 modules, can hold ~53 alphanumeric chars
    // Version 2 = 25x25, ~32 chars (might be too small)
    // Наши данные: ~55 символов, нужна версия 3
    
    uint8_t qrcodeData[qrcode_getBufferSize(3)];
    qrcode_initText(&qrcode, qrcodeData, 3, ECC_LOW, data);
    
    // Размер QR кода
    int moduleSize = 2;  // пикселей на модуль
    int qrSize = qrcode.size * moduleSize;
    
    // Центрируем QR код (оставляя место справа для текста)
    int offsetX = 2;
    int offsetY = (SCREEN_HEIGHT - qrSize) / 2;
    
    // Белый фон для QR
    display.fillRect(offsetX - 2, offsetY - 2, qrSize + 4, qrSize + 4, SSD1306_WHITE);
    
    // Рисуем модули
    for (int y = 0; y < qrcode.size; y++) {
        for (int x = 0; x < qrcode.size; x++) {
            if (qrcode_getModule(&qrcode, x, y)) {
                display.fillRect(
                    offsetX + x * moduleSize,
                    offsetY + y * moduleSize,
                    moduleSize,
                    moduleSize,
                    SSD1306_BLACK
                );
            }
        }
    }
}

void drawConnectingScreen() {
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("Connecting to WiFi"));
    
    display.setCursor(0, 14);
    display.println(config.wifi_ssid);
    
    // Анимация
    int dots = (millis() / 500) % 4;
    display.setCursor(0, 30);
    display.print(F("Please wait"));
    for (int i = 0; i < dots; i++) {
        display.print(F("."));
    }
    
    // Прогресс
    display.setCursor(0, 45);
    display.print(F("Attempt: "));
    display.print(connectionAttempts + 1);
    display.print(F("/"));
    display.println(MAX_CONNECTION_ATTEMPTS);
    
    // Прогресс-бар
    int progress = ((millis() - lastLedToggle) * 100) / 15000;
    drawProgressBar(0, 55, 128, 8, min(progress, 100));
}

void drawStatusScreen() {
    // Заголовок с WiFi иконкой
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.print(DEVICE_UID);
    
    // WiFi сила сигнала
    int rssi = WiFi.RSSI();
    drawWiFiIcon(100, 0, rssi);
    
    // Разделитель
    display.drawLine(0, 10, 128, 10, SSD1306_WHITE);
    
    // IP адрес
    display.setCursor(0, 14);
    display.print(F("IP: "));
    display.println(WiFi.localIP());
    
    // Сервер
    display.setCursor(0, 26);
    display.print(F("Srv: "));
    if (serverConnected) {
        display.println(F("OK"));
    } else {
        display.print(F("ERR("));
        display.print(serverErrors);
        display.println(F(")"));
    }
    
    // Uptime
    display.setCursor(0, 38);
    display.print(F("Up: "));
    unsigned long hours = uptimeSeconds / 3600;
    unsigned long mins = (uptimeSeconds % 3600) / 60;
    unsigned long secs = uptimeSeconds % 60;
    if (hours > 0) {
        display.print(hours);
        display.print(F("h "));
    }
    display.print(mins);
    display.print(F("m "));
    display.print(secs);
    display.println(F("s"));
    
    // Имя устройства
    if (strlen(config.device_name) > 0) {
        display.setCursor(0, 52);
        display.println(config.device_name);
    }
}

void drawSensorsScreen() {
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("=== SENSORS ==="));
    
    // Температура
    display.setCursor(0, 14);
    display.print(F("Temp: "));
    display.print(lastTemperature, 1);
    display.println(F(" C"));
    
    // Влажность воздуха
    display.setCursor(0, 26);
    display.print(F("Hum:  "));
    display.print(lastHumidity, 1);
    display.println(F(" %"));
    
    // Влажность почвы с прогресс-баром
    display.setCursor(0, 38);
    display.print(F("Soil: "));
    display.print((int)lastSoilMoisture);
    display.println(F(" %"));
    drawProgressBar(60, 38, 60, 8, (int)lastSoilMoisture);
    
    // Освещённость
    display.setCursor(0, 52);
    display.print(F("Light: "));
    display.print((int)lastLightLevel);
    display.println(F(" lux"));
}

void drawDevicesScreen() {
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("=== DEVICES ==="));
    
    // Левая колонка
    display.setCursor(0, 14);
    display.print(pumpOn ? F("[X]") : F("[ ]"));
    display.println(F(" Pump"));
    
    display.setCursor(0, 26);
    display.print(fanOn ? F("[X]") : F("[ ]"));
    display.println(F(" Fan"));
    
    display.setCursor(0, 38);
    display.print(heaterOn ? F("[X]") : F("[ ]"));
    display.println(F(" Heater"));
    
    // Правая колонка
    display.setCursor(64, 14);
    display.print(lightOn ? F("[X]") : F("[ ]"));
    display.println(F(" Light"));
    
    display.setCursor(64, 26);
    display.print(humidifierOn ? F("[X]") : F("[ ]"));
    display.println(F(" Humid"));
    
    display.setCursor(64, 38);
    display.print(coolerOn ? F("[X]") : F("[ ]"));
    display.println(F(" Cooler"));
    
    // Статус
    display.setCursor(0, 52);
    int activeCount = pumpOn + fanOn + heaterOn + lightOn + humidifierOn + coolerOn;
    display.print(F("Active: "));
    display.print(activeCount);
    display.println(F("/6"));
}

void drawErrorScreen(const char* error) {
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("!!! ERROR !!!"));
    
    display.setCursor(0, 20);
    display.println(error);
    
    display.setCursor(0, 40);
    display.println(F("Switching to"));
    display.setCursor(0, 52);
    display.println(F("Setup Mode..."));
}

void drawProgressBar(int x, int y, int width, int height, int percent) {
    percent = constrain(percent, 0, 100);
    display.drawRect(x, y, width, height, SSD1306_WHITE);
    int fillWidth = (width - 2) * percent / 100;
    display.fillRect(x + 1, y + 1, fillWidth, height - 2, SSD1306_WHITE);
}

void drawWiFiIcon(int x, int y, int rssi) {
    // Рисуем иконку WiFi на основе силы сигнала
    int bars = 0;
    if (rssi > -50) bars = 4;
    else if (rssi > -60) bars = 3;
    else if (rssi > -70) bars = 2;
    else if (rssi > -80) bars = 1;
    
    for (int i = 0; i < 4; i++) {
        int barHeight = 2 + i * 2;
        int barX = x + i * 5;
        int barY = y + 8 - barHeight;
        
        if (i < bars) {
            display.fillRect(barX, barY, 3, barHeight, SSD1306_WHITE);
        } else {
            display.drawRect(barX, barY, 3, barHeight, SSD1306_WHITE);
        }
    }
}

// ==================== BUTTON HANDLING ====================

void checkButton() {
    static bool lastButtonState = HIGH;
    bool buttonState = digitalRead(BUTTON_PIN);
    
    if (buttonState == LOW) {
        if (buttonPressTime == 0) {
            buttonPressTime = millis();
        } else if (millis() - buttonPressTime >= BUTTON_HOLD_TIME) {
            // Долгое нажатие - сброс настроек
            display.clearDisplay();
            display.setTextSize(2);
            display.setCursor(20, 25);
            display.println(F("RESET!"));
            display.display();
            delay(1000);
            clearConfig();
        }
    } else {
        // Кнопка отпущена
        if (buttonPressTime > 0 && millis() - buttonPressTime < 1000) {
            // Короткое нажатие - переключение экрана
            if (currentState == STATE_AP_MODE) {
                // В режиме AP переключаемся между инфо и QR
                if (currentScreen == SCREEN_AP_MODE) {
                    currentScreen = SCREEN_QR_CODE;
                } else {
                    currentScreen = SCREEN_AP_MODE;
                }
            } else if (currentState == STATE_WORKING) {
                // В рабочем режиме переключаем экраны статуса
                if (currentScreen == SCREEN_STATUS) {
                    currentScreen = SCREEN_SENSORS;
                } else if (currentScreen == SCREEN_SENSORS) {
                    currentScreen = SCREEN_DEVICES;
                } else {
                    currentScreen = SCREEN_STATUS;
                }
            }
            lastScreenSwitch = millis();
        }
        buttonPressTime = 0;
    }
    
    lastButtonState = buttonState;
}

// ==================== EEPROM FUNCTIONS ====================

void loadConfig() {
    EEPROM.get(0, config);
}

void saveConfig() {
    config.magic = 0x4748;
    config.checksum = calculateChecksum();
    EEPROM.put(0, config);
    EEPROM.commit();
}

void clearConfig() {
    memset(&config, 0, sizeof(config));
    EEPROM.put(0, config);
    EEPROM.commit();
    ESP.restart();
}

uint8_t calculateChecksum() {
    uint8_t sum = 0;
    uint8_t* ptr = (uint8_t*)&config;
    for (size_t i = 0; i < sizeof(config) - 1; i++) {
        sum += ptr[i];
    }
    return sum;
}

bool isConfigValid() {
    if (config.magic != 0x4748) return false;
    if (strlen(config.wifi_ssid) == 0) return false;
    if (strlen(config.server_host) == 0) return false;
    if (config.checksum != calculateChecksum()) return false;
    return true;
}

// ==================== AP MODE ====================

void startAPMode() {
    WiFi.mode(WIFI_AP);
    String apSSID = String("Greenhouse-") + DEVICE_UID;
    WiFi.softAP(apSSID.c_str(), AP_PASSWORD);
    
    webServer.on("/", HTTP_GET, handleRoot);
    webServer.on("/scan", HTTP_GET, handleScan);
    webServer.on("/configure", HTTP_POST, handleConfigure);
    webServer.on("/configure", HTTP_OPTIONS, []() {
        webServer.sendHeader("Access-Control-Allow-Origin", "*");
        webServer.sendHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
        webServer.sendHeader("Access-Control-Allow-Headers", "Content-Type");
        webServer.send(204);
    });
    webServer.on("/status", HTTP_GET, handleStatus);
    webServer.on("/reset", HTTP_POST, handleReset);
    
    webServer.begin();
}

void setupStatusServer() {
    webServer.on("/status", HTTP_GET, handleStatus);
    webServer.on("/reset", HTTP_POST, handleReset);
    webServer.on("/sensors", HTTP_GET, []() {
        StaticJsonDocument<256> doc;
        doc["temperature"] = lastTemperature;
        doc["humidity"] = lastHumidity;
        doc["soil_moisture"] = lastSoilMoisture;
        doc["light_level"] = lastLightLevel;
        
        String response;
        serializeJson(doc, response);
        
        webServer.sendHeader("Access-Control-Allow-Origin", "*");
        webServer.send(200, "application/json", response);
    });
    webServer.begin();
}

// ==================== WEB HANDLERS ====================

void handleRoot() {
    String html = R"(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greenhouse Setup</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               margin: 0; padding: 20px; background: linear-gradient(135deg, #1B5E20 0%, #4CAF50 100%);
               min-height: 100vh; }
        .container { max-width: 400px; margin: 0 auto; }
        .card { background: white; border-radius: 16px; padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
        h1 { text-align: center; margin-bottom: 24px; color: #1B5E20; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 500; color: #333; }
        input, select { width: 100%; padding: 12px; border: 2px solid #e0e0e0;
                       border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        input:focus, select:focus { border-color: #4CAF50; outline: none; }
        button { width: 100%; padding: 14px; background: linear-gradient(135deg, #1B5E20 0%, #4CAF50 100%);
                color: white; border: none; border-radius: 8px; font-size: 16px;
                font-weight: 600; cursor: pointer; margin-top: 16px; }
        button:hover { opacity: 0.9; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .networks { margin-bottom: 16px; }
        .network-item { padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px;
                       margin-bottom: 8px; cursor: pointer; display: flex;
                       justify-content: space-between; align-items: center; }
        .network-item:hover { border-color: #4CAF50; background: #f8fff8; }
        .network-item.selected { border-color: #1B5E20; background: #e8f5e9; }
        .signal { color: #666; }
        .status { text-align: center; padding: 16px; margin-top: 16px;
                 border-radius: 8px; display: none; }
        .status.success { display: block; background: #e8f5e9; color: #1B5E20; }
        .status.error { display: block; background: #ffebee; color: #c62828; }
        .status.loading { display: block; background: #fff3e0; color: #e65100; }
        .device-info { text-align: center; color: #666; font-size: 14px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Greenhouse Setup</h1>
            <div class="device-info">Device: )" + String(DEVICE_UID) + R"(</div>
            
            <div class="networks" id="networks">
                <label>Available WiFi Networks</label>
                <div id="network-list">Scanning...</div>
            </div>
            
            <form id="configForm">
                <div class="form-group">
                    <label>WiFi Network (SSID)</label>
                    <input type="text" id="ssid" name="ssid" required>
                </div>
                
                <div class="form-group">
                    <label>WiFi Password</label>
                    <input type="password" id="password" name="password">
                </div>
                
                <div class="form-group">
                    <label>Server Address</label>
                    <input type="text" id="server" name="server" placeholder="192.168.1.100" required>
                </div>
                
                <div class="form-group">
                    <label>Server Port</label>
                    <input type="number" id="port" name="port" value="8000" required>
                </div>
                
                <div class="form-group">
                    <label>Device Name (optional)</label>
                    <input type="text" id="name" name="name" placeholder="My Greenhouse">
                </div>
                
                <button type="submit" id="submitBtn">Save & Connect</button>
            </form>
            
            <div id="status" class="status"></div>
        </div>
    </div>
    
    <script>
        fetch('/scan').then(r => r.json()).then(data => {
            const list = document.getElementById('network-list');
            if (data.networks && data.networks.length > 0) {
                list.innerHTML = data.networks.map(n => 
                    `<div class="network-item" onclick="selectNetwork('${n.ssid}')">
                        <span>${n.ssid}</span>
                        <span class="signal">${n.rssi} dBm ${n.encrypted ? '🔒' : ''}</span>
                    </div>`
                ).join('');
            } else {
                list.innerHTML = '<div style="color:#666">No networks found</div>';
            }
        }).catch(() => {
            document.getElementById('network-list').innerHTML = '<div style="color:#666">Scan failed</div>';
        });
        
        function selectNetwork(ssid) {
            document.getElementById('ssid').value = ssid;
            document.querySelectorAll('.network-item').forEach(el => {
                el.classList.remove('selected');
                if (el.textContent.includes(ssid)) el.classList.add('selected');
            });
        }
        
        document.getElementById('configForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const status = document.getElementById('status');
            const btn = document.getElementById('submitBtn');
            status.className = 'status loading';
            status.textContent = 'Saving configuration...';
            btn.disabled = true;
            
            const data = {
                ssid: document.getElementById('ssid').value,
                password: document.getElementById('password').value,
                server: document.getElementById('server').value,
                port: parseInt(document.getElementById('port').value),
                name: document.getElementById('name').value
            };
            
            fetch('/configure', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(r => r.json()).then(result => {
                if (result.success) {
                    status.className = 'status success';
                    status.textContent = 'Configuration saved! Device will restart...';
                } else {
                    status.className = 'status error';
                    status.textContent = 'Error: ' + (result.error || 'Unknown error');
                    btn.disabled = false;
                }
            }).catch(err => {
                status.className = 'status error';
                status.textContent = 'Connection error. Please try again.';
                btn.disabled = false;
            });
        });
    </script>
</body>
</html>
)";
    
    webServer.send(200, "text/html", html);
}

void handleScan() {
    StaticJsonDocument<1024> doc;
    JsonArray networks = doc.createNestedArray("networks");
    
    int n = WiFi.scanNetworks();
    
    for (int i = 0; i < n && i < 15; i++) {
        JsonObject network = networks.createNestedObject();
        network["ssid"] = WiFi.SSID(i);
        network["rssi"] = WiFi.RSSI(i);
        network["encrypted"] = (WiFi.encryptionType(i) != ENC_TYPE_NONE);
    }
    
    String response;
    serializeJson(doc, response);
    
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "application/json", response);
}

void handleConfigure() {
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    
    if (!webServer.hasArg("plain")) {
        webServer.send(400, "application/json", "{\"success\":false,\"error\":\"No data\"}");
        return;
    }
    
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, webServer.arg("plain"));
    
    if (error) {
        webServer.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid JSON\"}");
        return;
    }
    
    if (!doc.containsKey("ssid") || !doc.containsKey("server")) {
        webServer.send(400, "application/json", "{\"success\":false,\"error\":\"Missing required fields\"}");
        return;
    }
    
    strncpy(config.wifi_ssid, doc["ssid"] | "", sizeof(config.wifi_ssid) - 1);
    strncpy(config.wifi_password, doc["password"] | "", sizeof(config.wifi_password) - 1);
    strncpy(config.server_host, doc["server"] | "", sizeof(config.server_host) - 1);
    config.server_port = doc["port"] | 8000;
    strncpy(config.device_name, doc["name"] | "", sizeof(config.device_name) - 1);
    
    saveConfig();
    
    webServer.send(200, "application/json", "{\"success\":true,\"message\":\"Configuration saved. Restarting...\"}");
    
    // Показываем на дисплее
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 20);
    display.println(F("Config saved!"));
    display.setCursor(0, 35);
    display.println(F("Restarting..."));
    display.display();
    
    delay(1000);
    ESP.restart();
}

void handleStatus() {
    StaticJsonDocument<512> doc;
    
    doc["device_uid"] = DEVICE_UID;
    doc["device_name"] = config.device_name;
    doc["state"] = (int)currentState;
    doc["wifi_connected"] = (WiFi.status() == WL_CONNECTED);
    doc["uptime"] = uptimeSeconds;
    
    if (WiFi.status() == WL_CONNECTED) {
        doc["ip_address"] = WiFi.localIP().toString();
        doc["wifi_ssid"] = WiFi.SSID();
        doc["wifi_rssi"] = WiFi.RSSI();
    }
    
    doc["server_host"] = config.server_host;
    doc["server_port"] = config.server_port;
    doc["server_connected"] = serverConnected;
    doc["server_errors"] = serverErrors;
    
    JsonObject devices = doc.createNestedObject("devices");
    devices["pump"] = pumpOn;
    devices["fan"] = fanOn;
    devices["heater"] = heaterOn;
    devices["light"] = lightOn;
    devices["humidifier"] = humidifierOn;
    devices["cooler"] = coolerOn;
    
    JsonObject sensors = doc.createNestedObject("sensors");
    sensors["temperature"] = lastTemperature;
    sensors["humidity"] = lastHumidity;
    sensors["soil_moisture"] = lastSoilMoisture;
    sensors["light_level"] = lastLightLevel;
    
    String response;
    serializeJson(doc, response);
    
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "application/json", response);
}

void handleReset() {
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "application/json", "{\"success\":true,\"message\":\"Resetting configuration...\"}");
    delay(500);
    clearConfig();
}

// ==================== STATION MODE ====================

void startStationMode() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(config.wifi_ssid, config.wifi_password);
    lastLedToggle = millis();
}

// ==================== LED INDICATION ====================

void updateLED() {
    unsigned long currentMillis = millis();
    
    switch (currentState) {
        case STATE_AP_MODE:
            if (currentMillis - lastLedToggle >= 100) {
                ledState = !ledState;
                digitalWrite(LED_PIN, ledState ? LED_ON : LED_OFF);
                lastLedToggle = currentMillis;
            }
            break;
            
        case STATE_CONNECTING:
            if (currentMillis - lastLedToggle >= 500) {
                ledState = !ledState;
                digitalWrite(LED_PIN, ledState ? LED_ON : LED_OFF);
                lastLedToggle = currentMillis;
            }
            break;
            
        case STATE_CONNECTION_FAILED:
            {
                int phase = (currentMillis / 150) % 6;
                digitalWrite(LED_PIN, (phase == 0 || phase == 2) ? LED_ON : LED_OFF);
            }
            break;
            
        case STATE_WORKING:
            digitalWrite(LED_PIN, LED_ON);
            break;
            
        default:
            digitalWrite(LED_PIN, LED_OFF);
            break;
    }
}

// ==================== SENSORS ====================

void readSensors() {
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    
    if (!isnan(temp)) {
        lastTemperature = temp;
    }
    
    if (!isnan(hum)) {
        lastHumidity = hum;
    }
    
    int soilRaw = analogRead(SOIL_MOISTURE_PIN);
    lastSoilMoisture = map(soilRaw, 1024, 300, 0, 100);
    lastSoilMoisture = constrain(lastSoilMoisture, 0, 100);
    
    lastLightLevel = 400; // Заглушка
}

// ==================== SERVER COMMUNICATION ====================

void sendDataToServer() {
    if (WiFi.status() != WL_CONNECTED) {
        return;
    }
    
    HTTPClient http;
    String url = String("http://") + config.server_host + ":" + config.server_port + "/api/v1/sensors/data";
    
    http.begin(wifiClient, url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);
    
    StaticJsonDocument<256> doc;
    doc["temperature"] = lastTemperature;
    doc["humidity"] = lastHumidity;
    doc["soil_moisture"] = lastSoilMoisture;
    doc["light_level"] = lastLightLevel;
    doc["device_id"] = DEVICE_UID;
    if (strlen(config.device_name) > 0) {
        doc["device_name"] = config.device_name;
    }
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    int httpCode = http.POST(jsonString);
    
    if (httpCode > 0 && httpCode == HTTP_CODE_OK) {
        serverConnected = true;
        serverErrors = 0;
        String response = http.getString();
        parseServerResponse(response);
    } else {
        serverConnected = false;
        serverErrors++;
    }
    
    http.end();
}

void parseServerResponse(String response) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (error) {
        return;
    }
    
    JsonArray commands = doc["commands"];
    for (JsonObject cmd : commands) {
        const char* device = cmd["device"];
        const char* action = cmd["action"];
        int duration = cmd["duration"] | 0;
        executeCommand(device, action, duration);
    }
}

void checkServerCommands() {
    if (WiFi.status() != WL_CONNECTED) {
        return;
    }
    
    HTTPClient http;
    String url = String("http://") + config.server_host + ":" + config.server_port + "/api/v1/devices/commands/pending";
    
    http.begin(wifiClient, url);
    http.setTimeout(5000);
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
                executeCommand(device, action, 0);
            }
        }
    }
    
    http.end();
}

// ==================== DEVICE CONTROL ====================

void executeCommand(const char* device, const char* action, int duration) {
    bool turnOn = (strcmp(action, "on") == 0);
    
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
}

void setFan(bool on) {
    fanOn = on;
    digitalWrite(RELAY_FAN, on ? LOW : HIGH);
}

void setHeater(bool on) {
    heaterOn = on;
    digitalWrite(RELAY_HEATER, on ? LOW : HIGH);
}

void setLight(bool on) {
    lightOn = on;
    digitalWrite(RELAY_LIGHT, on ? LOW : HIGH);
}

void setHumidifier(bool on) {
    humidifierOn = on;
    digitalWrite(RELAY_HUMIDIFIER, on ? LOW : HIGH);
}

void setCooler(bool on) {
    coolerOn = on;
    digitalWrite(RELAY_COOLER, on ? LOW : HIGH);
}

// ==================== DEVICE TIMERS ====================

void checkDeviceTimers() {
    if (pumpOn && pumpDuration > 0) {
        if (millis() - pumpStartTime >= pumpDuration) {
            setPump(false);
            pumpDuration = 0;
        }
    }
}
