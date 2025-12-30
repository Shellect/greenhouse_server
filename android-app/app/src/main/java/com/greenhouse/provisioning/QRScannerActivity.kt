package com.greenhouse.provisioning

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.util.Size
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.greenhouse.provisioning.databinding.ActivityQrScannerBinding
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Экран сканирования QR кода
 * Использует CameraX и ML Kit для распознавания QR кодов
 */
class QRScannerActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityQrScannerBinding
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var barcodeScanner: BarcodeScanner
    
    private var isScanning = true
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityQrScannerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupCamera()
        setupUI()
    }
    
    private fun setupUI() {
        binding.backButton.setOnClickListener {
            finish()
        }
    }
    
    private fun setupCamera() {
        cameraExecutor = Executors.newSingleThreadExecutor()
        
        val options = BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
        
        barcodeScanner = BarcodeScanning.getClient(options)
        
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            bindCameraUseCases(cameraProvider)
        }, ContextCompat.getMainExecutor(this))
    }
    
    private fun bindCameraUseCases(cameraProvider: ProcessCameraProvider) {
        val preview = Preview.Builder()
            .build()
            .also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
        
        val imageAnalysis = ImageAnalysis.Builder()
            .setTargetResolution(Size(1280, 720))
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            .also {
                it.setAnalyzer(cameraExecutor, QRCodeAnalyzer { qrContent ->
                    handleQrCodeScanned(qrContent)
                })
            }
        
        val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
        
        try {
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                this,
                cameraSelector,
                preview,
                imageAnalysis
            )
        } catch (e: Exception) {
            Toast.makeText(
                this,
                "Failed to start camera: ${e.message}",
                Toast.LENGTH_LONG
            ).show()
        }
    }
    
    private fun handleQrCodeScanned(qrContent: String) {
        if (!isScanning) return
        
        val deviceInfo = DeviceInfo.fromQrCode(qrContent)
        
        if (deviceInfo != null) {
            isScanning = false
            
            runOnUiThread {
                // Переходим к экрану подключения WiFi
                val intent = Intent(this, WifiSetupActivity::class.java).apply {
                    putExtra(EXTRA_DEVICE_INFO, deviceInfo)
                }
                startActivity(intent)
                finish()
            }
        } else {
            runOnUiThread {
                Toast.makeText(
                    this,
                    R.string.invalid_qr_code,
                    Toast.LENGTH_SHORT
                ).show()
            }
            
            // Даём время на показ toast и продолжаем сканирование
            binding.root.postDelayed({
                isScanning = true
            }, 2000)
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        barcodeScanner.close()
    }
    
    /**
     * Анализатор изображений для распознавания QR кодов
     */
    private inner class QRCodeAnalyzer(
        private val onQrCodeScanned: (String) -> Unit
    ) : ImageAnalysis.Analyzer {
        
        @SuppressLint("UnsafeOptInUsageError")
        override fun analyze(imageProxy: ImageProxy) {
            val mediaImage = imageProxy.image
            
            if (mediaImage != null && isScanning) {
                val image = InputImage.fromMediaImage(
                    mediaImage,
                    imageProxy.imageInfo.rotationDegrees
                )
                
                barcodeScanner.process(image)
                    .addOnSuccessListener { barcodes ->
                        for (barcode in barcodes) {
                            barcode.rawValue?.let { value ->
                                onQrCodeScanned(value)
                                return@addOnSuccessListener
                            }
                        }
                    }
                    .addOnCompleteListener {
                        imageProxy.close()
                    }
            } else {
                imageProxy.close()
            }
        }
    }
    
    companion object {
        const val EXTRA_DEVICE_INFO = "device_info"
    }
}

