/**
 * 🍓 Strawberry Greenhouse - Frontend Application
 * Умная теплица для выращивания клубники
 */

// ==================== Configuration ====================
const API_BASE = '/api/v1';
const UPDATE_INTERVAL = 5000; // 5 seconds

// Device icons mapping
const DEVICE_ICONS = {
    pump: '💧',
    fan: '🌀',
    heater: '🔥',
    cooler: '❄️',
    light: '💡',
    humidifier: '💨',
    dehumidifier: '🌫️'
};

// Device names mapping
const DEVICE_NAMES = {
    pump: 'Полив',
    fan: 'Вентиляция',
    heater: 'Обогрев',
    cooler: 'Охлаждение',
    light: 'Освещение',
    humidifier: 'Увлажнитель',
    dehumidifier: 'Осушитель'
};

// Growth stage info
const GROWTH_STAGES = {
    seedling: { icon: '🌱', name: 'Рассада' },
    vegetative: { icon: '🌿', name: 'Вегетация' },
    flowering: { icon: '🌸', name: 'Цветение' },
    fruiting: { icon: '🍓', name: 'Плодоношение' },
    dormant: { icon: '❄️', name: 'Покой' }
};

// Optimal ranges for sensors
const SENSOR_RANGES = {
    temperature: { min: 18, max: 25, criticalLow: 5, criticalHigh: 35 },
    humidity: { min: 60, max: 75, criticalLow: 40, criticalHigh: 90 },
    soil_moisture: { min: 60, max: 80, criticalLow: 40, criticalHigh: 95 },
    light_level: { min: 200, max: 600, criticalLow: 0, criticalHigh: 1000 }
};

// ==================== State ====================
let currentState = {
    connected: false,
    healthScore: 0,
    growthStage: 'vegetative',
    devices: [],
    alerts: [],
    recommendations: []
};

// ==================== DOM Elements ====================
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    currentTime: document.getElementById('currentTime'),
    healthScore: document.getElementById('healthScore'),
    healthRing: document.getElementById('healthRing'),
    growthStage: document.getElementById('growthStage'),
    alertsBadge: document.getElementById('alertsBadge'),
    devicesGrid: document.getElementById('devicesGrid'),
    growthStages: document.getElementById('growthStages'),
    recommendationsList: document.getElementById('recommendationsList'),
    alertsList: document.getElementById('alertsList'),
    lastUpdate: document.getElementById('lastUpdate'),
    // Sensor elements
    temperature: document.getElementById('temperature'),
    temperatureBar: document.getElementById('temperatureBar'),
    humidity: document.getElementById('humidity'),
    humidityBar: document.getElementById('humidityBar'),
    soilMoisture: document.getElementById('soilMoisture'),
    soilMoistureBar: document.getElementById('soilMoistureBar'),
    lightLevel: document.getElementById('lightLevel'),
    lightBar: document.getElementById('lightBar')
};

// ==================== API Functions ====================

/**
 * Fetch greenhouse status
 */
async function fetchStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');
        return await response.json();
    } catch (error) {
        console.error('Error fetching status:', error);
        throw error;
    }
}

/**
 * Fetch active alerts
 */
async function fetchAlerts() {
    try {
        const response = await fetch(`${API_BASE}/alerts`);
        if (!response.ok) throw new Error('Failed to fetch alerts');
        return await response.json();
    } catch (error) {
        console.error('Error fetching alerts:', error);
        return [];
    }
}

/**
 * Send device command
 */
async function sendDeviceCommand(deviceType, action, deviceId = 'main') {
    try {
        const response = await fetch(`${API_BASE}/devices/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_type: deviceType,
                device_id: deviceId,
                action: action
            })
        });
        if (!response.ok) throw new Error('Failed to send command');
        return await response.json();
    } catch (error) {
        console.error('Error sending command:', error);
        throw error;
    }
}

/**
 * Toggle auto mode for device
 */
async function setAutoMode(deviceType, enabled, deviceId = 'main') {
    try {
        const response = await fetch(
            `${API_BASE}/devices/${deviceType}/auto?enabled=${enabled}&device_id=${deviceId}`,
            { method: 'POST' }
        );
        if (!response.ok) throw new Error('Failed to set auto mode');
        return await response.json();
    } catch (error) {
        console.error('Error setting auto mode:', error);
        throw error;
    }
}

/**
 * Update control settings (including growth stage)
 */
async function updateControlSettings(settings) {
    try {
        const response = await fetch(`${API_BASE}/control/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (!response.ok) throw new Error('Failed to update settings');
        return await response.json();
    } catch (error) {
        console.error('Error updating settings:', error);
        throw error;
    }
}

/**
 * Acknowledge alert
 */
async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to acknowledge alert');
        return await response.json();
    } catch (error) {
        console.error('Error acknowledging alert:', error);
        throw error;
    }
}

// ==================== UI Update Functions ====================

/**
 * Update connection status
 */
function updateConnectionStatus(connected) {
    currentState.connected = connected;
    const el = elements.connectionStatus;
    
    if (connected) {
        el.classList.add('connected');
        el.classList.remove('error');
        el.querySelector('.status-text').textContent = 'Подключено';
    } else {
        el.classList.remove('connected');
        el.classList.add('error');
        el.querySelector('.status-text').textContent = 'Ошибка связи';
    }
}

/**
 * Update current time display
 */
function updateTime() {
    const now = new Date();
    elements.currentTime.textContent = now.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Update health score display
 */
function updateHealthScore(score) {
    currentState.healthScore = score;
    elements.healthScore.textContent = Math.round(score);
    
    // Update ring progress
    const circumference = 2 * Math.PI * 54; // r=54
    const offset = circumference - (score / 100) * circumference;
    elements.healthRing.style.strokeDashoffset = offset;
    
    // Update color based on score
    let color;
    if (score >= 80) {
        color = '#2ecc71';
    } else if (score >= 60) {
        color = '#f39c12';
    } else {
        color = '#e74c3c';
    }
    elements.healthRing.style.stroke = color;
    elements.healthScore.style.color = color;
}

/**
 * Update growth stage display
 */
function updateGrowthStage(stage) {
    currentState.growthStage = stage;
    const stageInfo = GROWTH_STAGES[stage] || GROWTH_STAGES.vegetative;
    
    const el = elements.growthStage;
    el.querySelector('.stage-icon').textContent = stageInfo.icon;
    el.querySelector('.stage-name').textContent = stageInfo.name;
    
    // Update stage buttons
    document.querySelectorAll('.stage-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.stage === stage);
    });
}

/**
 * Update sensor displays
 */
function updateSensors(readings) {
    if (!readings) return;
    
    // Temperature
    if (readings.temperature !== null && readings.temperature !== undefined) {
        elements.temperature.textContent = readings.temperature.toFixed(1);
        updateSensorBar('temperature', readings.temperature, elements.temperatureBar);
    }
    
    // Humidity
    if (readings.humidity !== null && readings.humidity !== undefined) {
        elements.humidity.textContent = readings.humidity.toFixed(0);
        updateSensorBar('humidity', readings.humidity, elements.humidityBar);
    }
    
    // Soil moisture
    if (readings.soil_moisture !== null && readings.soil_moisture !== undefined) {
        elements.soilMoisture.textContent = readings.soil_moisture.toFixed(0);
        updateSensorBar('soil_moisture', readings.soil_moisture, elements.soilMoistureBar);
    }
    
    // Light level
    if (readings.light_level !== null && readings.light_level !== undefined) {
        elements.lightLevel.textContent = Math.round(readings.light_level);
        updateSensorBar('light_level', readings.light_level, elements.lightBar);
    }
}

/**
 * Update sensor bar fill
 */
function updateSensorBar(sensorType, value, barElement) {
    const range = SENSOR_RANGES[sensorType];
    if (!range) return;
    
    // Calculate percentage based on full range
    const fullRange = range.criticalHigh - range.criticalLow;
    const percent = Math.max(0, Math.min(100, ((value - range.criticalLow) / fullRange) * 100));
    
    barElement.style.width = `${percent}%`;
    
    // Update status class
    barElement.classList.remove('warning', 'danger');
    const card = barElement.closest('.sensor-card');
    card.removeAttribute('data-status');
    
    if (value < range.criticalLow || value > range.criticalHigh) {
        barElement.classList.add('danger');
        card.dataset.status = 'danger';
    } else if (value < range.min || value > range.max) {
        barElement.classList.add('warning');
        card.dataset.status = 'warning';
    }
}

/**
 * Render devices
 */
function renderDevices(devices) {
    currentState.devices = devices;
    
    if (!devices || devices.length === 0) {
        elements.devicesGrid.innerHTML = '<p class="no-devices">Нет устройств</p>';
        return;
    }
    
    elements.devicesGrid.innerHTML = devices.map(device => {
        const icon = DEVICE_ICONS[device.device_type] || '⚙️';
        const name = DEVICE_NAMES[device.device_type] || device.device_type;
        const isOn = device.status === 'on';
        
        return `
            <div class="device-card ${isOn ? 'active' : ''}" data-device="${device.device_type}" data-id="${device.device_id}">
                <div class="device-header">
                    <div class="device-info">
                        <span class="device-icon">${icon}</span>
                        <span class="device-name">${name}</span>
                    </div>
                    <span class="device-status ${device.status}">${isOn ? 'ВКЛ' : 'ВЫКЛ'}</span>
                </div>
                <div class="device-controls">
                    <button class="device-btn on-btn" onclick="handleDeviceAction('${device.device_type}', 'on', '${device.device_id}')">ВКЛ</button>
                    <button class="device-btn off-btn" onclick="handleDeviceAction('${device.device_type}', 'off', '${device.device_id}')">ВЫКЛ</button>
                </div>
                <div class="device-auto">
                    <span>Авто режим</span>
                    <label class="auto-toggle">
                        <input type="checkbox" ${device.auto_mode ? 'checked' : ''} 
                               onchange="handleAutoToggle('${device.device_type}', this.checked, '${device.device_id}')">
                        <span class="auto-slider"></span>
                    </label>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render recommendations
 */
function renderRecommendations(recommendations) {
    currentState.recommendations = recommendations;
    
    if (!recommendations || recommendations.length === 0) {
        elements.recommendationsList.innerHTML = '<li class="recommendation-item">Всё в порядке! Продолжайте в том же духе 🌱</li>';
        return;
    }
    
    elements.recommendationsList.innerHTML = recommendations.map(rec => 
        `<li class="recommendation-item">${rec}</li>`
    ).join('');
}

/**
 * Render alerts
 */
function renderAlerts(alerts) {
    currentState.alerts = alerts;
    
    // Update badge
    const badge = elements.alertsBadge;
    if (alerts && alerts.length > 0) {
        badge.style.display = 'flex';
        badge.querySelector('.alerts-count').textContent = alerts.length;
    } else {
        badge.style.display = 'none';
    }
    
    // Render alerts list
    if (!alerts || alerts.length === 0) {
        elements.alertsList.innerHTML = '<div class="no-alerts">Нет активных оповещений</div>';
        return;
    }
    
    elements.alertsList.innerHTML = alerts.map(alert => {
        const icon = alert.level === 'critical' ? '🚨' : alert.level === 'warning' ? '⚠️' : 'ℹ️';
        const time = new Date(alert.timestamp).toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div class="alert-item ${alert.level}" data-id="${alert.id}">
                <span class="alert-icon">${icon}</span>
                <div class="alert-content">
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${time}</div>
                </div>
                <button class="alert-dismiss" onclick="handleDismissAlert(${alert.id})" title="Подтвердить">✓</button>
            </div>
        `;
    }).join('');
}

/**
 * Update last update time
 */
function updateLastUpdateTime() {
    elements.lastUpdate.textContent = new Date().toLocaleTimeString('ru-RU');
}

// ==================== Event Handlers ====================

/**
 * Handle device action button click
 */
async function handleDeviceAction(deviceType, action, deviceId) {
    try {
        await sendDeviceCommand(deviceType, action, deviceId);
        await refreshData();
    } catch (error) {
        alert('Ошибка при отправке команды');
    }
}

/**
 * Handle auto mode toggle
 */
async function handleAutoToggle(deviceType, enabled, deviceId) {
    try {
        await setAutoMode(deviceType, enabled, deviceId);
        await refreshData();
    } catch (error) {
        alert('Ошибка при изменении режима');
    }
}

/**
 * Handle growth stage selection
 */
async function handleStageSelect(stage) {
    try {
        await updateControlSettings({
            growth_stage: stage,
            auto_watering: true,
            auto_ventilation: true,
            auto_heating: true,
            auto_lighting: true
        });
        updateGrowthStage(stage);
        await refreshData();
    } catch (error) {
        alert('Ошибка при изменении стадии роста');
    }
}

/**
 * Handle alert dismissal
 */
async function handleDismissAlert(alertId) {
    try {
        await acknowledgeAlert(alertId);
        await refreshData();
    } catch (error) {
        alert('Ошибка при подтверждении оповещения');
    }
}

// ==================== Main Functions ====================

/**
 * Refresh all data
 */
async function refreshData() {
    try {
        const [status, alerts] = await Promise.all([
            fetchStatus(),
            fetchAlerts()
        ]);
        
        updateConnectionStatus(true);
        updateHealthScore(status.health_score);
        updateGrowthStage(status.growth_stage);
        updateSensors(status.current_readings);
        renderDevices(status.devices);
        renderRecommendations(status.recommendations);
        renderAlerts(alerts);
        updateLastUpdateTime();
        
    } catch (error) {
        updateConnectionStatus(false);
        console.error('Error refreshing data:', error);
    }
}

/**
 * Initialize application
 */
function init() {
    // Update time every second
    updateTime();
    setInterval(updateTime, 1000);
    
    // Set up stage button listeners
    document.querySelectorAll('.stage-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            handleStageSelect(btn.dataset.stage);
        });
    });
    
    // Initial data fetch
    refreshData();
    
    // Set up auto-refresh
    setInterval(refreshData, UPDATE_INTERVAL);
    
    console.log('🍓 Greenhouse Dashboard initialized');
}

// Make handlers available globally
window.handleDeviceAction = handleDeviceAction;
window.handleAutoToggle = handleAutoToggle;
window.handleDismissAlert = handleDismissAlert;

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', init);

