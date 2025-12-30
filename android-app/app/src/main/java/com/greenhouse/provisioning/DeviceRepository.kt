package com.greenhouse.provisioning

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Repository для взаимодействия с устройством NodeMCU
 */
class DeviceRepository {
    
    private var apiService: DeviceApiService? = null
    
    /**
     * Инициализирует подключение к устройству
     * IP устройства в режиме AP всегда 192.168.4.1
     */
    fun initialize(deviceIp: String = "192.168.4.1") {
        val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .build()
        
        val retrofit = Retrofit.Builder()
            .baseUrl("http://$deviceIp/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        
        apiService = retrofit.create(DeviceApiService::class.java)
    }
    
    /**
     * Сканирует доступные WiFi сети
     */
    suspend fun scanNetworks(): Result<List<WifiNetworkInfo>> = withContext(Dispatchers.IO) {
        try {
            val api = apiService ?: return@withContext Result.failure(
                IllegalStateException("Repository not initialized")
            )
            
            val response = api.scanNetworks()
            
            if (response.isSuccessful && response.body() != null) {
                val networks = response.body()!!.networks.map { network ->
                    WifiNetworkInfo(
                        ssid = network.ssid,
                        rssi = network.rssi,
                        isEncrypted = network.encrypted
                    )
                }.sortedByDescending { it.rssi }
                
                Result.success(networks)
            } else {
                Result.failure(Exception("Failed to scan networks: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Отправляет конфигурацию на устройство
     */
    suspend fun configure(config: WifiConfiguration): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val api = apiService ?: return@withContext Result.failure(
                IllegalStateException("Repository not initialized")
            )
            
            val request = ConfigureRequest(
                ssid = config.ssid,
                password = config.password,
                server = config.serverAddress,
                port = config.serverPort,
                name = config.deviceName
            )
            
            val response = api.configure(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(true)
            } else {
                val error = response.body()?.error ?: "Unknown error"
                Result.failure(Exception(error))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Получает статус устройства
     */
    suspend fun getStatus(): Result<DeviceStatus> = withContext(Dispatchers.IO) {
        try {
            val api = apiService ?: return@withContext Result.failure(
                IllegalStateException("Repository not initialized")
            )
            
            val response = api.getStatus()
            
            if (response.isSuccessful && response.body() != null) {
                val status = response.body()!!
                Result.success(DeviceStatus(
                    deviceUid = status.deviceUid,
                    deviceName = status.deviceName,
                    state = status.state,
                    wifiConnected = status.wifiConnected,
                    ipAddress = status.ipAddress,
                    wifiSsid = status.wifiSsid,
                    wifiRssi = status.wifiRssi,
                    serverHost = status.serverHost,
                    serverPort = status.serverPort,
                    devices = status.devices,
                    sensors = status.sensors
                ))
            } else {
                Result.failure(Exception("Failed to get status: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Проверяет, доступно ли устройство
     */
    suspend fun isDeviceReachable(): Boolean = withContext(Dispatchers.IO) {
        try {
            val api = apiService ?: return@withContext false
            val response = api.getStatus()
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }
}

