package com.greenhouse.provisioning

import com.google.gson.annotations.SerializedName
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

/**
 * API для взаимодействия с NodeMCU в режиме AP
 */
interface DeviceApiService {
    
    /**
     * Получить список доступных WiFi сетей
     */
    @GET("/scan")
    suspend fun scanNetworks(): Response<ScanResponse>
    
    /**
     * Отправить конфигурацию WiFi
     */
    @POST("/configure")
    suspend fun configure(@Body config: ConfigureRequest): Response<ConfigureResponse>
    
    /**
     * Получить статус устройства
     */
    @GET("/status")
    suspend fun getStatus(): Response<StatusResponse>
    
    /**
     * Сбросить настройки устройства
     */
    @POST("/reset")
    suspend fun reset(): Response<ResetResponse>
}

// ============ Request/Response Models ============

data class ScanResponse(
    val networks: List<NetworkItem>
)

data class NetworkItem(
    val ssid: String,
    val rssi: Int,
    val encrypted: Boolean
)

data class ConfigureRequest(
    val ssid: String,
    val password: String,
    val server: String,
    val port: Int,
    val name: String = ""
)

data class ConfigureResponse(
    val success: Boolean,
    val message: String? = null,
    val error: String? = null
)

data class StatusResponse(
    @SerializedName("device_uid")
    val deviceUid: String,
    
    @SerializedName("device_name")
    val deviceName: String?,
    
    val state: Int,
    
    @SerializedName("wifi_connected")
    val wifiConnected: Boolean,
    
    @SerializedName("ip_address")
    val ipAddress: String?,
    
    @SerializedName("wifi_ssid")
    val wifiSsid: String?,
    
    @SerializedName("wifi_rssi")
    val wifiRssi: Int?,
    
    @SerializedName("server_host")
    val serverHost: String?,
    
    @SerializedName("server_port")
    val serverPort: Int?,
    
    val devices: Map<String, Boolean>?,
    val sensors: Map<String, Float>?
)

data class ResetResponse(
    val success: Boolean,
    val message: String? = null
)

