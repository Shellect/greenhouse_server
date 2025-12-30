package com.greenhouse.provisioning

import android.os.Parcelable
import kotlinx.parcelize.Parcelize

/**
 * Информация об устройстве, извлечённая из QR кода
 * 
 * Формат QR кода:
 * GREENHOUSE:UID=GH-0001;SSID=Greenhouse-GH-0001;PWD=greenhouse2024
 */
@Parcelize
data class DeviceInfo(
    val uid: String,           // Уникальный ID устройства (GH-XXXX)
    val apSsid: String,        // SSID точки доступа устройства
    val apPassword: String     // Пароль точки доступа
) : Parcelable {
    
    companion object {
        private const val PREFIX = "GREENHOUSE:"
        private const val KEY_UID = "UID"
        private const val KEY_SSID = "SSID"
        private const val KEY_PWD = "PWD"
        
        /**
         * Парсит QR код и возвращает DeviceInfo или null если формат неверный
         */
        fun fromQrCode(qrContent: String): DeviceInfo? {
            if (!qrContent.startsWith(PREFIX)) {
                return null
            }
            
            val data = qrContent.removePrefix(PREFIX)
            val params = mutableMapOf<String, String>()
            
            data.split(";").forEach { part ->
                val keyValue = part.split("=", limit = 2)
                if (keyValue.size == 2) {
                    params[keyValue[0].trim()] = keyValue[1].trim()
                }
            }
            
            val uid = params[KEY_UID] ?: return null
            val ssid = params[KEY_SSID] ?: return null
            val password = params[KEY_PWD] ?: return null
            
            return DeviceInfo(uid, ssid, password)
        }
        
        /**
         * Генерирует QR код для устройства
         */
        fun toQrCode(uid: String, apPassword: String = "greenhouse2024"): String {
            val ssid = "Greenhouse-$uid"
            return "$PREFIX$KEY_UID=$uid;$KEY_SSID=$ssid;$KEY_PWD=$apPassword"
        }
    }
}

/**
 * Конфигурация WiFi для передачи на устройство
 */
data class WifiConfiguration(
    val ssid: String,
    val password: String,
    val serverAddress: String,
    val serverPort: Int,
    val deviceName: String = ""
)

/**
 * Информация о WiFi сети (результат сканирования)
 */
data class WifiNetworkInfo(
    val ssid: String,
    val rssi: Int,
    val isEncrypted: Boolean
) {
    val signalStrength: SignalStrength
        get() = when {
            rssi >= -50 -> SignalStrength.EXCELLENT
            rssi >= -60 -> SignalStrength.GOOD
            rssi >= -70 -> SignalStrength.FAIR
            else -> SignalStrength.WEAK
        }
}

enum class SignalStrength {
    EXCELLENT, GOOD, FAIR, WEAK
}

/**
 * Состояние устройства (ответ от /status)
 */
data class DeviceStatus(
    val deviceUid: String,
    val deviceName: String?,
    val state: Int,
    val wifiConnected: Boolean,
    val ipAddress: String?,
    val wifiSsid: String?,
    val wifiRssi: Int?,
    val serverHost: String?,
    val serverPort: Int?,
    val devices: Map<String, Boolean>?,
    val sensors: Map<String, Float>?
)

