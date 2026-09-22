/*
 * BHOOMI - Soil Health Probe Simulation
 * ESP32 + pH / EC / Moisture / Light / Soil Temp / Air Temp+Humidity / Soil-type switch
 * WiFi-based (BLE removed for this version — Wokwi cannot simulate BLE)
 *
 * NOTE ON SIM vs REAL HARDWARE:
 *  - Real DHT11 -> here we use Wokwi's DHT22 part (Wokwi has no DHT11 part).
 *    The DHT.h library call below is set to DHT22 for the simulation.
 *    On real hardware, change DHTTYPE to DHT11 - no other code changes needed.
 *  - pH / EC / Moisture are simulated with potentiometers (0-3.3V) standing in
 *    for the analog sensor outputs. Swap in real ADC calibration curves later.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------------- Pin map ----------------
#define PIN_PH        34
#define PIN_MOISTURE  35
#define PIN_EC        32
#define PIN_LDR       33
#define PIN_DS18B20    4
#define PIN_DHT       15
#define PIN_SOIL_SW   27
#define PIN_BUZZER    26
#define I2C_SDA       21
#define I2C_SCL       22

#define DHTTYPE DHT22   // sim uses DHT22 part; change to DHT11 on real hardware

// ---------------- WiFi / backend ----------------
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const char* BACKEND_URL   = "https://httpbin.org/post"; // dummy endpoint for sim testing

// ---------------- Objects ----------------
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(PIN_DHT, DHTTYPE);
OneWire oneWire(PIN_DS18B20);
DallasTemperature soilTempSensor(&oneWire);

// ---------------- Moving average buffers ----------------
const int SAMPLES = 50;
float phBuf[SAMPLES], ecBuf[SAMPLES], moistBuf[SAMPLES];
int sampleIndex = 0;
bool bufferFilled = false;

// ---------------- Thresholds (example, tune later) ----------------
const float PH_LOW = 5.5, PH_HIGH = 7.5;
const float EC_HIGH = 2.0;      // dS/m
const float MOISTURE_LOW = 25.0; // %

unsigned long lastReadingMillis = 0;
const unsigned long READ_INTERVAL_MS = 2000;

// ---------------- Helpers ----------------
float readAveraged(float buf[]) {
  int n = bufferFilled ? SAMPLES : sampleIndex;
  if (n == 0) return 0;
  float sum = 0;
  for (int i = 0; i < n; i++) sum += buf[i];
  return sum / n;
}

float adcToPh(int raw) {
  // Placeholder linear mapping: 0-4095 -> pH 0-14
  return (raw / 4095.0) * 14.0;
}

float adcToEC(int raw) {
  // Placeholder linear mapping: 0-4095 -> 0-5 dS/m
  return (raw / 4095.0) * 5.0;
}

float adcToMoisturePercent(int raw) {
  // Capacitive sensor: higher raw ~ drier, invert to get %
  return 100.0 - ((raw / 4095.0) * 100.0);
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection failed (continuing offline).");
  }
}

void sendReadingToBackend(float ph, float ec, float moisture, float soilTemp,
                           float airTemp, float airHum, int lightRaw, int soilType,
                           float limeKgPerAcre, float gypsumKgPerAcre) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Skipping upload: WiFi not connected.");
    return;
  }
  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = "{";
  payload += "\"ph\":" + String(ph, 2) + ",";
  payload += "\"ec\":" + String(ec, 2) + ",";
  payload += "\"moisture\":" + String(moisture, 1) + ",";
  payload += "\"soil_temp\":" + String(soilTemp, 1) + ",";
  payload += "\"air_temp\":" + String(airTemp, 1) + ",";
  payload += "\"air_humidity\":" + String(airHum, 1) + ",";
  payload += "\"light_raw\":" + String(lightRaw) + ",";
  payload += "\"soil_type\":" + String(soilType) + ",";
  payload += "\"lime_kg_per_acre\":" + String(limeKgPerAcre, 1) + ",";
  payload += "\"gypsum_kg_per_acre\":" + String(gypsumKgPerAcre, 1);
  payload += "}";

  int httpCode = http.POST(payload);
  Serial.print("POST status: ");
  Serial.println(httpCode);
  http.end();
}

// ---------------- Setup ----------------
void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(PIN_SOIL_SW, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  Wire.begin(I2C_SDA, I2C_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("BHOOMI Booting");

  dht.begin();
  soilTempSensor.begin();

  connectWiFi();

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("BHOOMI Ready");
  delay(1000);
  lcd.clear();
}

// ---------------- Main loop ----------------
void loop() {
  if (millis() - lastReadingMillis < READ_INTERVAL_MS) return;
  lastReadingMillis = millis();

  // --- Raw analog reads ---
  int phRaw   = analogRead(PIN_PH);
  int ecRaw   = analogRead(PIN_EC);
  int moistRaw = analogRead(PIN_MOISTURE);
  int lightRaw = analogRead(PIN_LDR);

  // --- Push into moving-average buffers ---
  phBuf[sampleIndex]    = adcToPh(phRaw);
  ecBuf[sampleIndex]    = adcToEC(ecRaw);
  moistBuf[sampleIndex] = adcToMoisturePercent(moistRaw);
  sampleIndex++;
  if (sampleIndex >= SAMPLES) {
    sampleIndex = 0;
    bufferFilled = true;
  }

  float phAvg  = readAveraged(phBuf);
  float ecAvg  = readAveraged(ecBuf);
  float moistAvg = readAveraged(moistBuf);

  // --- DHT11/22 (air) ---
  float airTemp = dht.readTemperature();
  float airHum  = dht.readHumidity();
  if (isnan(airTemp) || isnan(airHum)) {
    Serial.println("DHT read failed.");
    airTemp = 0; airHum = 0;
  }

  // --- DS18B20 (soil temp) ---
  soilTempSensor.requestTemperatures();
  float soilTemp = soilTempSensor.getTempCByIndex(0);

  // --- Soil type switch (0 = one type, 1 = other) ---
  int soilType = digitalRead(PIN_SOIL_SW);

  // --- Rule engine: priority pH -> EC -> moisture ---
  String primaryAlert = "OK";
  bool buzz = false;
  float limeKgPerAcre = 0, gypsumKgPerAcre = 0;

  if (phAvg < PH_LOW) {
    primaryAlert = "pH Low: Add Lime";
    limeKgPerAcre = (PH_LOW - phAvg) * 400.0; // placeholder dosage formula
    buzz = true;
  } else if (phAvg > PH_HIGH) {
    primaryAlert = "pH High: Gypsum";
    gypsumKgPerAcre = (phAvg - PH_HIGH) * 350.0; // placeholder dosage formula
    buzz = true;
  } else if (ecAvg > EC_HIGH) {
    primaryAlert = "EC High: Salinity";
    buzz = true;
  } else if (moistAvg < MOISTURE_LOW) {
    primaryAlert = "Moisture Low";
    buzz = true;
  }

  digitalWrite(PIN_BUZZER, buzz ? HIGH : LOW);

  // --- LCD output ---
  lcd.clear();
  if ((millis() / 2000) % 2 == 0) {
    // Screen 1: pH, EC, and Alert
    lcd.setCursor(0, 0);
    lcd.print("pH:" + String(phAvg, 1) + " EC:" + String(ecAvg, 1));
    lcd.setCursor(0, 1);
    lcd.print(primaryAlert.substring(0, 16));
  } else {
    // Screen 2: Moisture, Soil Temp, & Air Temp
    lcd.setCursor(0, 0);
    lcd.print("M:" + String(moistAvg, 0) + "% ST:" + String(soilTemp, 1) + "C");
    lcd.setCursor(0, 1);
    lcd.print("AT:" + String(airTemp, 1) + "C H:" + String(airHum, 0) + "%");
  }
}