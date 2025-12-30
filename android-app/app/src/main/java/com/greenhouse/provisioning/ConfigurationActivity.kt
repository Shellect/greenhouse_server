package com.greenhouse.provisioning

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.lifecycleScope
import com.greenhouse.provisioning.databinding.ActivityConfigurationBinding
import kotlinx.coroutines.launch

/**
 * Экран конфигурации устройства
 * Позволяет выбрать WiFi сеть и ввести настройки сервера
 */
class ConfigurationActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityConfigurationBinding
    private lateinit var deviceRepository: DeviceRepository
    private lateinit var wifiManager: WifiConnectionManager
    
    private var deviceInfo: DeviceInfo? = null
    private var availableNetworks: List<WifiNetworkInfo> = emptyList()
    private var selectedNetwork: WifiNetworkInfo? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityConfigurationBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        deviceRepository = DeviceRepository()
        deviceRepository.initialize()
        
        wifiManager = WifiConnectionManager(this)
        
        @Suppress("DEPRECATION")
        deviceInfo = intent.getParcelableExtra(QRScannerActivity.EXTRA_DEVICE_INFO)
        
        if (deviceInfo == null) {
            showError("Invalid device info")
            return
        }
        
        setupUI()
        scanNetworks()
    }
    
    private fun setupUI() {
        binding.deviceIdText.text = deviceInfo?.uid ?: ""
        
        // Network selection dropdown
        binding.networkDropdown.setOnItemClickListener { _, _, position, _ ->
            if (position < availableNetworks.size) {
                selectedNetwork = availableNetworks[position]
                binding.ssidInput.setText(selectedNetwork?.ssid)
                validateForm()
            }
        }
        
        // Refresh networks button
        binding.refreshButton.setOnClickListener {
            scanNetworks()
        }
        
        // Form validation
        binding.ssidInput.doAfterTextChanged { validateForm() }
        binding.serverInput.doAfterTextChanged { validateForm() }
        binding.portInput.doAfterTextChanged { validateForm() }
        
        // Save button
        binding.saveButton.setOnClickListener {
            hideKeyboard()
            saveConfiguration()
        }
        
        // Cancel button
        binding.cancelButton.setOnClickListener {
            confirmCancel()
        }
        
        // Set default port
        binding.portInput.setText("8000")
    }
    
    private fun validateForm(): Boolean {
        val ssid = binding.ssidInput.text?.toString()?.trim() ?: ""
        val server = binding.serverInput.text?.toString()?.trim() ?: ""
        val port = binding.portInput.text?.toString()?.trim() ?: ""
        
        val isValid = ssid.isNotEmpty() && server.isNotEmpty() && port.isNotEmpty()
        binding.saveButton.isEnabled = isValid
        
        return isValid
    }
    
    private fun scanNetworks() {
        binding.networkProgress.visibility = View.VISIBLE
        binding.refreshButton.isEnabled = false
        binding.networkDropdown.isEnabled = false
        binding.networkDropdown.hint = getString(R.string.scanning_networks)
        
        lifecycleScope.launch {
            val result = deviceRepository.scanNetworks()
            
            runOnUiThread {
                binding.networkProgress.visibility = View.GONE
                binding.refreshButton.isEnabled = true
                binding.networkDropdown.isEnabled = true
                
                if (result.isSuccess) {
                    availableNetworks = result.getOrNull() ?: emptyList()
                    
                    if (availableNetworks.isEmpty()) {
                        binding.networkDropdown.hint = getString(R.string.no_networks_found)
                    } else {
                        binding.networkDropdown.hint = getString(R.string.select_network)
                        
                        // Создаём адаптер для dropdown
                        val networkNames = availableNetworks.map { network ->
                            val signalIcon = when (network.signalStrength) {
                                SignalStrength.EXCELLENT -> "📶"
                                SignalStrength.GOOD -> "📶"
                                SignalStrength.FAIR -> "📶"
                                SignalStrength.WEAK -> "📶"
                            }
                            val lockIcon = if (network.isEncrypted) "🔒" else ""
                            "${network.ssid} $signalIcon $lockIcon"
                        }
                        
                        val adapter = ArrayAdapter(
                            this@ConfigurationActivity,
                            android.R.layout.simple_dropdown_item_1line,
                            networkNames
                        )
                        binding.networkDropdown.setAdapter(adapter)
                    }
                } else {
                    Toast.makeText(
                        this@ConfigurationActivity,
                        "Failed to scan networks: ${result.exceptionOrNull()?.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }
    
    private fun saveConfiguration() {
        if (!validateForm()) return
        
        val ssid = binding.ssidInput.text?.toString()?.trim() ?: return
        val password = binding.passwordInput.text?.toString() ?: ""
        val server = binding.serverInput.text?.toString()?.trim() ?: return
        val port = binding.portInput.text?.toString()?.toIntOrNull() ?: 8000
        val deviceName = binding.deviceNameInput.text?.toString()?.trim() ?: ""
        
        val config = WifiConfiguration(
            ssid = ssid,
            password = password,
            serverAddress = server,
            serverPort = port,
            deviceName = deviceName
        )
        
        showSavingProgress()
        
        lifecycleScope.launch {
            val result = deviceRepository.configure(config)
            
            runOnUiThread {
                hideSavingProgress()
                
                if (result.isSuccess) {
                    openSuccessScreen()
                } else {
                    showConfigurationError(result.exceptionOrNull()?.message ?: "Unknown error")
                }
            }
        }
    }
    
    private fun showSavingProgress() {
        binding.saveButton.isEnabled = false
        binding.saveButton.text = getString(R.string.status_saving)
        binding.savingProgress.visibility = View.VISIBLE
    }
    
    private fun hideSavingProgress() {
        binding.saveButton.isEnabled = true
        binding.saveButton.text = getString(R.string.save_config_button)
        binding.savingProgress.visibility = View.GONE
    }
    
    private fun showConfigurationError(error: String) {
        AlertDialog.Builder(this)
            .setTitle(R.string.error_title)
            .setMessage(getString(R.string.error_configuration_failed) + "\n\n$error")
            .setPositiveButton(R.string.retry_button) { _, _ -> saveConfiguration() }
            .setNegativeButton(R.string.cancel_button, null)
            .show()
    }
    
    private fun showError(message: String) {
        AlertDialog.Builder(this)
            .setTitle(R.string.error_title)
            .setMessage(message)
            .setPositiveButton(R.string.ok_button) { _, _ -> finish() }
            .setCancelable(false)
            .show()
    }
    
    private fun confirmCancel() {
        AlertDialog.Builder(this)
            .setTitle("Cancel Setup?")
            .setMessage("Are you sure you want to cancel? The device will remain unconfigured.")
            .setPositiveButton("Yes, Cancel") { _, _ ->
                wifiManager.disconnectFromDeviceNetwork()
                finish()
            }
            .setNegativeButton("Continue Setup", null)
            .show()
    }
    
    private fun openSuccessScreen() {
        // Отключаемся от сети устройства
        wifiManager.disconnectFromDeviceNetwork()
        
        val intent = Intent(this, SetupCompleteActivity::class.java).apply {
            putExtra(QRScannerActivity.EXTRA_DEVICE_INFO, deviceInfo)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        startActivity(intent)
        finish()
    }
    
    private fun hideKeyboard() {
        val imm = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
        currentFocus?.let {
            imm.hideSoftInputFromWindow(it.windowToken, 0)
        }
    }
    
    override fun onBackPressed() {
        confirmCancel()
    }
}

