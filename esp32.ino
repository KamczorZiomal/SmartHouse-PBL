#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <time.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// ===== CONFIGURATION =====
// WiFi credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Firebase configuration (from your Firebase project)
#define API_KEY "AIzaSyCDe0XoLJkGIi5xFqxZqHZRb68OOB3gi9U"
#define DATABASE_URL "https://smart-house-iot-2025-default-rtdb.europe-west1.firebasedatabase.app/"
#define USER_EMAIL "arduino-device@smart-house-iot-2025.com"  // Create this user in Firebase Auth
#define USER_PASSWORD "your_device_password"

// Device configuration
const String DEVICE_ID = "smart_house_001";
const String DEVICE_LOCATION = "Living Room";
const String DEVICE_FIRMWARE = "v1.2.3";

// Timing configuration
const unsigned long DATA_INTERVAL = 15000;  // 15 seconds
const unsigned long ALERT_INTERVAL = 60000; // 60 seconds

// ===== PIN CONFIGURATION =====
#define DHT_PIN 4           // DHT22 data pin
#define DHT_TYPE DHT22      // DHT22 sensor type
#define PIR_PIN 2           // PIR motion sensor
#define LDR_PIN 34          // LDR light sensor (analog)
#define MQ135_PIN 35        // MQ-135 air quality sensor (analog)
#define STATUS_LED 2        // Built-in LED
#define ALERT_LED 5         // External alert LED (optional)

// ===== SENSOR THRESHOLDS =====
const float TEMP_MAX = 30.0;
const float TEMP_MIN = 10.0;
const float TEMP_CRITICAL = 40.0;
const float HUMIDITY_MAX = 80.0;
const float HUMIDITY_MIN = 20.0;
const float HUMIDITY_CRITICAL = 90.0;
const float AIR_QUALITY_MAX = 70.0;
const float AIR_QUALITY_CRITICAL = 85.0;

// ===== GLOBAL VARIABLES =====
DHT dht(DHT_PIN, DHT_TYPE);
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

unsigned long lastDataTime = 0;
unsigned long lastAlertTime = 0;
int dataCount = 0;
int alertCount = 0;
bool isConnected = false;

String ipAddress = "";

// ===== SENSOR READING STRUCTURE =====
struct SensorData {
  float temperature;
  float humidity;
  float airQuality;
  int lightLevel;
  bool motionDetected;
  int batteryLevel;
  int signalStrength;
  unsigned long timestamp;
};

// ===== SETUP FUNCTION =====
void setup() {
  Serial.begin(115200);
  Serial.println("🔌 Starting Smart House Arduino Device...");
  
  // Initialize pins
  pinMode(PIR_PIN, INPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(ALERT_LED, OUTPUT);
  
  // Initialize sensors
  dht.begin();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Configure time
  configTime(0, 0, "pool.ntp.org");
  
  // Initialize Firebase
  initializeFirebase();
  
  Serial.println("✅ Initialization complete!");
  Serial.println("📡 Starting data transmission...");
  Serial.println("");
}

// ===== MAIN LOOP =====
void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected, reconnecting...");
    connectToWiFi();
  }
  
  // Send sensor data
  if (currentTime - lastDataTime >= DATA_INTERVAL) {
    sendSensorData();
    lastDataTime = currentTime;
  }
  
  // Check for alerts
  if (currentTime - lastAlertTime >= ALERT_INTERVAL) {
    checkAndSendAlerts();
    lastAlertTime = currentTime;
  }
  
  // Status LED blink
  digitalWrite(STATUS_LED, (millis() / 1000) % 2);
  
  delay(1000);
}

// ===== WIFI CONNECTION =====
void connectToWiFi() {
  Serial.print("🔗 Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ WiFi connected!");
    Serial.print("📍 IP Address: ");
    ipAddress = WiFi.localIP().toString();
    Serial.println(ipAddress);
    Serial.print("📶 Signal Strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    isConnected = true;
  } else {
    Serial.println();
    Serial.println("❌ WiFi connection failed!");
    isConnected = false;
  }
}

// ===== FIREBASE INITIALIZATION =====
void initializeFirebase() {
  Serial.println("🔥 Initializing Firebase...");
  
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  
  // Sign in with user credentials
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;
  
  config.token_status_callback = tokenStatusCallback;
  config.max_token_generation_retry = 5;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  Serial.println("✅ Firebase initialized!");
}

// ===== SENSOR DATA READING =====
SensorData readSensors() {
  SensorData data;
  
  // Read DHT22 (Temperature & Humidity)
  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  
  // Handle DHT22 read errors
  if (isnan(data.temperature)) {
    data.temperature = 22.0; // Default fallback
    Serial.println("⚠️ DHT22 temperature read error");
  }
  if (isnan(data.humidity)) {
    data.humidity = 50.0; // Default fallback
    Serial.println("⚠️ DHT22 humidity read error");
  }
  
  // Read air quality (MQ-135)
  int rawAirQuality = analogRead(MQ135_PIN);
  data.airQuality = map(rawAirQuality, 0, 4095, 0, 100); // Convert to percentage
  
  // Read light level (LDR)
  int rawLight = analogRead(LDR_PIN);
  data.lightLevel = map(rawLight, 0, 4095, 0, 1000); // Convert to lux approximation
  
  // Read motion detection (PIR)
  data.motionDetected = digitalRead(PIR_PIN);
  
  // Calculate battery level (using ADC reading from power supply)
  data.batteryLevel = calculateBatteryLevel();
  
  // Get WiFi signal strength
  data.signalStrength = WiFi.RSSI();
  
  // Set timestamp
  data.timestamp = getTimestamp();
  
  return data;
}

// ===== SEND SENSOR DATA TO FIREBASE =====
void sendSensorData() {
  if (!isConnected) return;
  
  SensorData data = readSensors();
  dataCount++;
  
  Serial.println("📡 [" + String(getTimeString()) + "] Sending data #" + String(dataCount) + ":");
  Serial.println("   🌡️  Temperature: " + String(data.temperature, 1) + "°C");
  Serial.println("   💧 Humidity: " + String(data.humidity, 1) + "%");
  Serial.println("   🌬️  Air Quality: " + String(data.airQuality, 1) + "%");
  Serial.println("   💡 Light: " + String(data.lightLevel) + " lux");
  Serial.println("   🚶 Motion: " + String(data.motionDetected ? "DETECTED!" : "none"));
  Serial.println("   🔋 Battery: " + String(data.batteryLevel) + "%");
  Serial.println("   📶 Signal: " + String(data.signalStrength) + " dBm");
  
  // Create JSON objects for Firebase
  FirebaseJson temperatureJson, humidityJson, motionJson, deviceJson, latestJson, historyJson, statusJson;
  
  // Temperature reading
  temperatureJson.set("temperature", data.temperature);
  temperatureJson.set("timestamp", data.timestamp);
  temperatureJson.set("deviceId", DEVICE_ID);
  temperatureJson.set("source", "arduino_hardware");
  temperatureJson.set("sourceType", "real_device");
  temperatureJson.set("isSimulated", false);
  
  // Humidity reading
  humidityJson.set("humidity", data.humidity);
  humidityJson.set("timestamp", data.timestamp);
  humidityJson.set("deviceId", DEVICE_ID);
  humidityJson.set("source", "arduino_hardware");
  humidityJson.set("sourceType", "real_device");
  humidityJson.set("isSimulated", false);
  
  // Motion reading
  motionJson.set("motionDetected", data.motionDetected);
  motionJson.set("timestamp", data.timestamp);
  motionJson.set("deviceId", DEVICE_ID);
  motionJson.set("source", "arduino_hardware");
  motionJson.set("sourceType", "real_device");
  motionJson.set("isSimulated", false);
  
  // Device status
  deviceJson.set("last_seen", data.timestamp);
  deviceJson.set("deviceId", DEVICE_ID);
  deviceJson.set("status", "online");
  deviceJson.set("ipAddress", ipAddress);
  deviceJson.set("source", "arduino_hardware");
  deviceJson.set("batteryLevel", data.batteryLevel);
  
  // Latest data
  latestJson.set("temperature", data.temperature);
  latestJson.set("humidity", data.humidity);
  latestJson.set("airQuality", data.airQuality);
  latestJson.set("lightLevel", data.lightLevel);
  latestJson.set("motionDetected", data.motionDetected);
  latestJson.set("batteryLevel", data.batteryLevel);
  latestJson.set("signalStrength", data.signalStrength);
  latestJson.set("timestamp", data.timestamp);
  latestJson.set("deviceId", DEVICE_ID);
  latestJson.set("location", DEVICE_LOCATION);
  latestJson.set("firmware", DEVICE_FIRMWARE);
  latestJson.set("ipAddress", ipAddress);
  latestJson.set("source", "arduino_hardware");
  latestJson.set("sourceType", "real_device");
  latestJson.set("isSimulated", false);
  latestJson.set("lastUpdated", data.timestamp);
  
  // History data (same as latest)
  historyJson = latestJson;
  
  // Status data
  statusJson.set("online", true);
  statusJson.set("lastSeen", data.timestamp);
  statusJson.set("dataCount", dataCount);
  
  // Send to Firebase
  bool success = true;
  
  // Send to individual reading collections
  if (!Firebase.RTDB.push(&fbdo, "temperature_readings", &temperatureJson)) {
    Serial.println("   ❌ Failed to send temperature data: " + fbdo.errorReason());
    success = false;
  }
  
  if (!Firebase.RTDB.push(&fbdo, "humidity_readings", &humidityJson)) {
    Serial.println("   ❌ Failed to send humidity data: " + fbdo.errorReason());
    success = false;
  }
  
  if (!Firebase.RTDB.push(&fbdo, "motion_readings", &motionJson)) {
    Serial.println("   ❌ Failed to send motion data: " + fbdo.errorReason());
    success = false;
  }
  
  // Send device status
  if (!Firebase.RTDB.set(&fbdo, "device_status/arduino_hardware", &deviceJson)) {
    Serial.println("   ❌ Failed to send device status: " + fbdo.errorReason());
    success = false;
  }
  
  // Send to device-specific paths
  String devicePath = "devices/" + DEVICE_ID;
  
  if (!Firebase.RTDB.set(&fbdo, devicePath + "/latest", &latestJson)) {
    Serial.println("   ❌ Failed to send latest data: " + fbdo.errorReason());
    success = false;
  }
  
  if (!Firebase.RTDB.set(&fbdo, devicePath + "/history/" + String(data.timestamp), &historyJson)) {
    Serial.println("   ❌ Failed to send history data: " + fbdo.errorReason());
    success = false;
  }
  
  if (!Firebase.RTDB.set(&fbdo, devicePath + "/status", &statusJson)) {
    Serial.println("   ❌ Failed to send status data: " + fbdo.errorReason());
    success = false;
  }
  
  if (success) {
    Serial.println("   ✅ Data sent to Firebase Realtime Database!");
    Serial.println("   📍 Paths: temperature_readings, humidity_readings, motion_readings");
    
    // Check thresholds
    checkThresholdsAndAlert(data);
  } else {
    Serial.println("   ⚠️ Some Firebase writes failed");
  }
  
  Serial.println("");
}

// ===== CHECK AND SEND ALERTS =====
void checkAndSendAlerts() {
  SensorData data = readSensors();
  
  // Check if any threshold is exceeded
  bool alertTriggered = false;
  String alertType = "";
  String alertMessage = "";
  String severity = "HIGH";
  
  if (data.temperature > TEMP_CRITICAL) {
    alertTriggered = true;
    alertType = "CRITICAL_TEMPERATURE";
    alertMessage = "KRYTYCZNA temperatura: " + String(data.temperature, 1) + "°C!";
    severity = "CRITICAL";
  } else if (data.temperature > TEMP_MAX) {
    alertTriggered = true;
    alertType = "HIGH_TEMPERATURE";
    alertMessage = "Wykryto wysoką temperaturę: " + String(data.temperature, 1) + "°C!";
    severity = "HIGH";
  } else if (data.humidity > HUMIDITY_CRITICAL) {
    alertTriggered = true;
    alertType = "CRITICAL_HUMIDITY";
    alertMessage = "KRYTYCZNA wilgotność: " + String(data.humidity, 1) + "%!";
    severity = "CRITICAL";
  } else if (data.humidity > HUMIDITY_MAX) {
    alertTriggered = true;
    alertType = "HIGH_HUMIDITY";
    alertMessage = "Wykryto wysoką wilgotność: " + String(data.humidity, 1) + "%!";
    severity = "HIGH";
  } else if (data.airQuality > AIR_QUALITY_CRITICAL) {
    alertTriggered = true;
    alertType = "CRITICAL_AIR_QUALITY";
    alertMessage = "KRYTYCZNA jakość powietrza: " + String(data.airQuality, 1) + "%!";
    severity = "CRITICAL";
  } else if (data.airQuality > AIR_QUALITY_MAX) {
    alertTriggered = true;
    alertType = "POOR_AIR_QUALITY";
    alertMessage = "Wykryto niską jakość powietrza: " + String(data.airQuality, 1) + "%!";
    severity = "MEDIUM";
  } else if (data.motionDetected) {
    alertTriggered = true;
    alertType = "MOTION_DETECTED";
    alertMessage = "Wykryto ruch w lokalizacji: " + DEVICE_LOCATION + "!";
    severity = "LOW";
  }
  
  if (alertTriggered) {
    sendAlert(data, alertType, alertMessage, severity);
  }
}

// ===== SEND ALERT TO FIREBASE =====
void sendAlert(SensorData data, String alertType, String alertMessage, String severity) {
  alertCount++;
  
  Serial.println("🚨 ==========================================");
  Serial.println("🚨 ALERT #" + String(alertCount) + " - " + severity + " CONDITIONS!");
  Serial.println("🚨 ==========================================");
  Serial.println("📍 Type: " + alertType);
  Serial.println("📝 Message: " + alertMessage);
  Serial.println("📍 Location: " + DEVICE_LOCATION);
  Serial.println("⏰ Time: " + getTimeString());
  
  // Light up alert LED
  digitalWrite(ALERT_LED, HIGH);
  delay(500);
  digitalWrite(ALERT_LED, LOW);
  
  unsigned long timestamp = getTimestamp();
  String alertId = "alert_" + String(timestamp);
  
  FirebaseJson alertJson;
  alertJson.set("type", alertType);
  alertJson.set("message", alertMessage);
  alertJson.set("original", alertMessage);
  alertJson.set("severity", severity);
  alertJson.set("timestamp", timestamp);
  alertJson.set("deviceId", DEVICE_ID);
  alertJson.set("temperature", data.temperature);
  alertJson.set("humidity", data.humidity);
  alertJson.set("airQuality", data.airQuality);
  alertJson.set("lightLevel", data.lightLevel);
  alertJson.set("motionDetected", data.motionDetected);
  alertJson.set("batteryLevel", data.batteryLevel);
  alertJson.set("signalStrength", data.signalStrength);
  alertJson.set("location", DEVICE_LOCATION);
  alertJson.set("firmware", DEVICE_FIRMWARE);
  alertJson.set("ipAddress", ipAddress);
  alertJson.set("source", "arduino_hardware");
  alertJson.set("sourceType", "real_device");
  alertJson.set("isSimulated", false);
  alertJson.set("processed", false);
  alertJson.set("alertId", alertId);
  alertJson.set("createdAt", timestamp);
  
  // Send to multiple Firebase paths
  bool success = true;
  
  if (!Firebase.RTDB.push(&fbdo, "alerts", &alertJson)) {
    Serial.println("🚨 ❌ Failed to send alert to general alerts: " + fbdo.errorReason());
    success = false;
  }
  
  if (!Firebase.RTDB.set(&fbdo, "threshold_alerts/" + alertId, &alertJson)) {
    Serial.println("🚨 ❌ Failed to send alert to threshold alerts: " + fbdo.errorReason());
    success = false;
  }
  
  String devicePath = "devices/" + DEVICE_ID;
  if (!Firebase.RTDB.set(&fbdo, devicePath + "/alerts/" + alertId, &alertJson)) {
    Serial.println("🚨 ❌ Failed to send alert to device alerts: " + fbdo.errorReason());
    success = false;
  }
  
  // Update device alert status
  FirebaseJson alertStatusJson;
  alertStatusJson.set("lastAlert", timestamp);
  alertStatusJson.set("alertCount", alertCount);
  alertStatusJson.set("currentSeverity", severity);
  
  if (!Firebase.RTDB.set(&fbdo, devicePath + "/status/alerts", &alertStatusJson)) {
    Serial.println("🚨 ❌ Failed to update alert status: " + fbdo.errorReason());
    success = false;
  }
  
  if (success) {
    Serial.println("🚨 ✅ ALERT SENT TO FIREBASE!");
    Serial.println("🚨 📍 Alert ID: " + alertId);
  }
  
  Serial.println("🚨 ==========================================");
  Serial.println("");
}

// ===== CHECK THRESHOLDS FOR IMMEDIATE ALERTS =====
void checkThresholdsAndAlert(SensorData data) {
  if (data.temperature > TEMP_MAX || 
      data.humidity > HUMIDITY_MAX || 
      data.airQuality > AIR_QUALITY_MAX) {
    Serial.println("⚠️ Threshold exceeded! Checking for alert...");
    checkAndSendAlerts();
  }
}

// ===== UTILITY FUNCTIONS =====
int calculateBatteryLevel() {
  // For USB powered devices, return high battery level
  // For battery powered, read from battery voltage divider
  return 95 + random(0, 5); // Simulated 95-100%
}

unsigned long getTimestamp() {
  time_t now;
  time(&now);
  return now * 1000; // Convert to milliseconds
}

String getTimeString() {
  time_t now;
  struct tm timeinfo;
  time(&now);
  localtime_r(&now, &timeinfo);
  
  char timeStr[50];
  strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(timeStr);
}

void tokenStatusCallback(TokenInfo info) {
  Serial.printf("Token info: type = %s, status = %s\n", getTokenType(info).c_str(), getTokenStatus(info).c_str());
}
