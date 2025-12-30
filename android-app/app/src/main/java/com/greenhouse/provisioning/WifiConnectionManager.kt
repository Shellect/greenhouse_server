package com.greenhouse.provisioning

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSpecifier
import android.os.Build
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeout
import kotlin.coroutines.resume

/**
 * Менеджер подключения к WiFi сетям
 * Используется для подключения к AP устройства NodeMCU
 */
class WifiConnectionManager(private val context: Context) {
    
    private val wifiManager: WifiManager = 
        context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    
    private val connectivityManager: ConnectivityManager = 
        context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    
    private var currentNetwork: Network? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    
    /**
     * Подключается к WiFi сети устройства (AP mode)
     * 
     * @param ssid SSID сети устройства (например, "Greenhouse-GH-0001")
     * @param password Пароль сети
     * @param timeoutMs Таймаут подключения в миллисекундах
     * @return true если подключение успешно
     */
    suspend fun connectToDeviceNetwork(
        ssid: String, 
        password: String, 
        timeoutMs: Long = 30000
    ): Result<Network> {
        return try {
            withTimeout(timeoutMs) {
                connectToWifiNetwork(ssid, password)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    private suspend fun connectToWifiNetwork(ssid: String, password: String): Result<Network> {
        // Убеждаемся что WiFi включен
        if (!wifiManager.isWifiEnabled) {
            return Result.failure(Exception("WiFi is disabled. Please enable WiFi."))
        }
        
        // Отключаем предыдущее подключение
        disconnectFromDeviceNetwork()
        
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // Android 10+ использует WifiNetworkSpecifier
            connectWithNetworkSpecifier(ssid, password)
        } else {
            // Для старых версий Android
            connectLegacy(ssid, password)
        }
    }
    
    private suspend fun connectWithNetworkSpecifier(
        ssid: String, 
        password: String
    ): Result<Network> = suspendCancellableCoroutine { continuation ->
        
        val specifier = WifiNetworkSpecifier.Builder()
            .setSsid(ssid)
            .setWpa2Passphrase(password)
            .build()
        
        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .setNetworkSpecifier(specifier)
            .build()
        
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                super.onAvailable(network)
                currentNetwork = network
                
                // Привязываем сетевые запросы к этой сети
                connectivityManager.bindProcessToNetwork(network)
                
                if (continuation.isActive) {
                    continuation.resume(Result.success(network))
                }
            }
            
            override fun onUnavailable() {
                super.onUnavailable()
                if (continuation.isActive) {
                    continuation.resume(Result.failure(
                        Exception("Network unavailable. Check SSID and password.")
                    ))
                }
            }
            
            override fun onLost(network: Network) {
                super.onLost(network)
                if (network == currentNetwork) {
                    currentNetwork = null
                    connectivityManager.bindProcessToNetwork(null)
                }
            }
        }
        
        networkCallback = callback
        
        try {
            connectivityManager.requestNetwork(request, callback)
        } catch (e: Exception) {
            if (continuation.isActive) {
                continuation.resume(Result.failure(e))
            }
        }
        
        continuation.invokeOnCancellation {
            try {
                connectivityManager.unregisterNetworkCallback(callback)
            } catch (e: Exception) {
                // Ignore
            }
        }
    }
    
    @Suppress("DEPRECATION")
    private suspend fun connectLegacy(ssid: String, password: String): Result<Network> {
        // Для Android 9 и ниже
        return suspendCancellableCoroutine { continuation ->
            try {
                val wifiConfig = android.net.wifi.WifiConfiguration().apply {
                    SSID = "\"$ssid\""
                    preSharedKey = "\"$password\""
                    allowedKeyManagement.set(android.net.wifi.WifiConfiguration.KeyMgmt.WPA_PSK)
                }
                
                val networkId = wifiManager.addNetwork(wifiConfig)
                if (networkId == -1) {
                    continuation.resume(Result.failure(Exception("Failed to add network configuration")))
                    return@suspendCancellableCoroutine
                }
                
                wifiManager.disconnect()
                val enabled = wifiManager.enableNetwork(networkId, true)
                wifiManager.reconnect()
                
                if (enabled) {
                    // Ждём подключения
                    val callback = object : ConnectivityManager.NetworkCallback() {
                        override fun onAvailable(network: Network) {
                            currentNetwork = network
                            if (continuation.isActive) {
                                continuation.resume(Result.success(network))
                            }
                        }
                        
                        override fun onUnavailable() {
                            if (continuation.isActive) {
                                continuation.resume(Result.failure(Exception("Failed to connect")))
                            }
                        }
                    }
                    
                    networkCallback = callback
                    
                    val request = NetworkRequest.Builder()
                        .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                        .build()
                    
                    connectivityManager.requestNetwork(request, callback)
                    
                    continuation.invokeOnCancellation {
                        try {
                            connectivityManager.unregisterNetworkCallback(callback)
                        } catch (e: Exception) {
                            // Ignore
                        }
                    }
                } else {
                    continuation.resume(Result.failure(Exception("Failed to enable network")))
                }
            } catch (e: Exception) {
                if (continuation.isActive) {
                    continuation.resume(Result.failure(e))
                }
            }
        }
    }
    
    /**
     * Отключается от сети устройства и восстанавливает обычное подключение
     */
    fun disconnectFromDeviceNetwork() {
        networkCallback?.let {
            try {
                connectivityManager.unregisterNetworkCallback(it)
            } catch (e: Exception) {
                // Callback already unregistered
            }
            networkCallback = null
        }
        
        currentNetwork = null
        
        // Отвязываем процесс от сети устройства
        connectivityManager.bindProcessToNetwork(null)
    }
    
    /**
     * Проверяет, подключены ли мы к сети устройства
     */
    fun isConnectedToDeviceNetwork(): Boolean {
        return currentNetwork != null
    }
    
    /**
     * Проверяет, включен ли WiFi
     */
    fun isWifiEnabled(): Boolean {
        return wifiManager.isWifiEnabled
    }
}

