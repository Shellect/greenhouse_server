package com.greenhouse.provisioning

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.greenhouse.provisioning.databinding.ActivityWifiSetupBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Экран подключения к WiFi сети устройства
 * Подключается к AP устройства и проверяет доступность
 */
class WifiSetupActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityWifiSetupBinding
    private lateinit var wifiManager: WifiConnectionManager
    private lateinit var deviceRepository: DeviceRepository
    
    private var deviceInfo: DeviceInfo? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWifiSetupBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        wifiManager = WifiConnectionManager(this)
        deviceRepository = DeviceRepository()
        
        @Suppress("DEPRECATION")
        deviceInfo = intent.getParcelableExtra(QRScannerActivity.EXTRA_DEVICE_INFO)
        
        if (deviceInfo == null) {
            showError("Invalid device info")
            return
        }
        
        setupUI()
        startConnection()
    }
    
    private fun setupUI() {
        binding.deviceIdText.text = deviceInfo?.uid ?: ""
        binding.statusText.text = getString(R.string.wifi_connecting)
        
        binding.cancelButton.setOnClickListener {
            wifiManager.disconnectFromDeviceNetwork()
            finish()
        }
        
        binding.retryButton.setOnClickListener {
            binding.retryButton.visibility = View.GONE
            startConnection()
        }
    }
    
    private fun startConnection() {
        val info = deviceInfo ?: return
        
        binding.progressIndicator.visibility = View.VISIBLE
        binding.statusIcon.visibility = View.GONE
        binding.statusText.text = getString(R.string.wifi_setup_subtitle, info.apSsid)
        
        lifecycleScope.launch {
            // Шаг 1: Подключение к WiFi устройства
            updateStatus("Connecting to ${info.apSsid}...")
            
            val connectionResult = wifiManager.connectToDeviceNetwork(
                ssid = info.apSsid,
                password = info.apPassword,
                timeoutMs = 30000
            )
            
            if (connectionResult.isFailure) {
                showConnectionFailed(connectionResult.exceptionOrNull()?.message ?: "Unknown error")
                return@launch
            }
            
            // Шаг 2: Ждём стабилизации соединения
            updateStatus("Verifying connection...")
            delay(2000)
            
            // Шаг 3: Инициализируем API клиент и проверяем доступность устройства
            deviceRepository.initialize()
            
            var deviceReachable = false
            repeat(5) { attempt ->
                updateStatus("Checking device (attempt ${attempt + 1}/5)...")
                if (deviceRepository.isDeviceReachable()) {
                    deviceReachable = true
                    return@repeat
                }
                delay(1000)
            }
            
            if (!deviceReachable) {
                showConnectionFailed("Device not responding. Make sure it's powered on.")
                return@launch
            }
            
            // Шаг 4: Получаем статус устройства
            updateStatus("Reading device status...")
            val statusResult = deviceRepository.getStatus()
            
            if (statusResult.isFailure) {
                showConnectionFailed("Failed to read device status")
                return@launch
            }
            
            // Успешное подключение - переходим к конфигурации
            showSuccess()
            delay(1000)
            
            openConfigurationScreen()
        }
    }
    
    private fun updateStatus(message: String) {
        runOnUiThread {
            binding.statusText.text = message
        }
    }
    
    private fun showConnectionFailed(error: String) {
        runOnUiThread {
            binding.progressIndicator.visibility = View.GONE
            binding.statusIcon.visibility = View.VISIBLE
            binding.statusIcon.setImageResource(R.drawable.ic_error)
            binding.statusText.text = getString(R.string.wifi_connection_failed)
            binding.errorDetails.visibility = View.VISIBLE
            binding.errorDetails.text = error
            binding.retryButton.visibility = View.VISIBLE
        }
    }
    
    private fun showSuccess() {
        runOnUiThread {
            binding.progressIndicator.visibility = View.GONE
            binding.statusIcon.visibility = View.VISIBLE
            binding.statusIcon.setImageResource(R.drawable.ic_success)
            binding.statusText.text = getString(R.string.wifi_connected)
        }
    }
    
    private fun showError(message: String) {
        AlertDialog.Builder(this)
            .setTitle(R.string.error_title)
            .setMessage(message)
            .setPositiveButton(R.string.ok_button) { _, _ -> finish() }
            .setCancelable(false)
            .show()
    }
    
    private fun openConfigurationScreen() {
        val intent = Intent(this, ConfigurationActivity::class.java).apply {
            putExtra(QRScannerActivity.EXTRA_DEVICE_INFO, deviceInfo)
        }
        startActivity(intent)
        finish()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Не отключаемся здесь, т.к. переходим к ConfigurationActivity
    }
}

