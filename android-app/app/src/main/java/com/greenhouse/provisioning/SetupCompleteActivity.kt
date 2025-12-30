package com.greenhouse.provisioning

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.greenhouse.provisioning.databinding.ActivitySetupCompleteBinding

/**
 * Экран успешного завершения настройки
 */
class SetupCompleteActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivitySetupCompleteBinding
    
    private var deviceInfo: DeviceInfo? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySetupCompleteBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        @Suppress("DEPRECATION")
        deviceInfo = intent.getParcelableExtra(QRScannerActivity.EXTRA_DEVICE_INFO)
        
        setupUI()
    }
    
    private fun setupUI() {
        binding.deviceIdText.text = deviceInfo?.uid ?: "Device"
        
        binding.doneButton.setOnClickListener {
            finishAffinity()
        }
        
        binding.addAnotherButton.setOnClickListener {
            // Возвращаемся на главный экран для добавления ещё одного устройства
            val intent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            startActivity(intent)
        }
    }
    
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        // Блокируем кнопку назад
        finishAffinity()
    }
}

