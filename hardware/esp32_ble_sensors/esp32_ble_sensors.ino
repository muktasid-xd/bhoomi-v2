/*
  ESP32 BLE Sensor Node — test prototype
  ---------------------------------------
  - Advertises one BLE service with two characteristics:
      COMMAND_CHAR  (laptop -> ESP32, WRITE)  : plain text sensor name, e.g. "DHT11", "SOIL_TEMP"
      DATA_CHAR     (ESP32 -> laptop, NOTIFY) : one JSON reading per notify

  - On receiving a command:
      1. Marks that sensor "active", replies is handled purely via state machine in loop()
      2. Waits 30s (stabilize)
      3. Sends 15 readings, 3s apart, each as its own JSON notify
      4. Returns to idle, ready for next command

  - DHT11 sends two separate JSON packets per tick (temp, humidity) since it's two values.
  - EC and pH sensors are not physically present yet -> stubs return null, but the
    JSON packet is still sent (with "value": null) so the pipeline/DB stays consistent.

  Required libraries (Arduino Library Manager):
    - ESP32 BLE Arduino (built into ESP32 board package)
    - DHT sensor library (Adafruit) + Adafruit Unified Sensor
    - OneWire
    - DallasTemperature
*/

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------- UUIDs (must match frontend exactly) ----------
#define SERVICE_UUID       "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define COMMAND_CHAR_UUID  "6e400002-b5a3-f393-e0a9-e50e24dcca9e" // write
#define DATA_CHAR_UUID     "6e400003-b5a3-f393-e0a9-e50e24dcca9e" // notify

// ---------- Pin config (adjust to your wiring) ----------
#define DHT11_PIN        4
#define DS18B20_PIN      5
#define SOIL_MOISTURE_PIN 34   // analog
#define LDR_PIN           35   // analog
// EC_PIN / PH_PIN not wired yet — sensors physically absent

DHT dht11(DHT11_PIN, DHT11);
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);

BLECharacteristic *dataChar;
bool deviceConnected = false;

// ---------- Session/reading state machine ----------
enum State { IDLE, STABILIZING, READING };
State state = IDLE;
String activeSensor = "";
unsigned long stateStartMillis = 0;
int readingIndex = 0;
const int TOTAL_READINGS = 15;
const unsigned long STABILIZE_MS = 30000;
const unsigned long READING_GAP_MS = 3000;

// ---------- BLE callbacks ----------
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* s) override { deviceConnected = true; }
  void onDisconnect(BLEServer* s) override {
    deviceConnected = false;
    BLEDevice::startAdvertising(); // resume advertising after disconnect
  }
};

class CommandCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String cmd = String(c->getValue().c_str());
    cmd.trim();
    if (cmd.length() == 0) return;

    // Ignore new commands while a cycle is already running
    if (state != IDLE) return;

    activeSensor = cmd;
    state = STABILIZING;
    stateStartMillis = millis();
    readingIndex = 0;

    if (activeSensor == "DHT11") dht11.begin();
    if (activeSensor == "SOIL_TEMP") ds18b20.begin();
  }
};

// ---------- Sensor read helpers: return NAN if unavailable ----------
float readSoilMoisture() {
  int raw = analogRead(SOIL_MOISTURE_PIN);
  return raw; // raw ADC value; calibrate to % later if needed
}

float readLight() {
  int raw = analogRead(LDR_PIN);
  return raw; // raw ADC value; calibrate to lux later if needed
}

float readSoilTemp() {
  ds18b20.requestTemperatures();
  float t = ds18b20.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C) return NAN;
  return t;
}

// EC / pH: hardware not present yet — stub returns NAN (-> JSON null)
float readEC()  { return NAN; }
float readPH()  { return NAN; }

// ---------- Build and send one JSON reading ----------
void sendReading(const String &sensorName, float value, const String &unit, int idx) {
  String json = "{";
  json += "\"sensor\":\"" + sensorName + "\",";
  if (isnan(value)) {
    json += "\"value\":null,";
  } else {
    json += "\"value\":" + String(value, 2) + ",";
  }
  json += "\"unit\":\"" + unit + "\",";
  json += "\"reading_index\":" + String(idx);
  json += "}";

  dataChar->setValue(json.c_str());
  dataChar->notify();
}

// Reads whichever sensor is active and sends the appropriate packet(s)
void takeReadingAndSend(int idx) {
  if (activeSensor == "DHT11") {
    float t = dht11.readTemperature();
    float h = dht11.readHumidity();
    sendReading("DHT11_temp", isnan(t) ? NAN : t, "C", idx);
    delay(50);
    sendReading("DHT11_humidity", isnan(h) ? NAN : h, "%", idx);
  } else if (activeSensor == "SOIL_MOISTURE") {
    sendReading("SOIL_MOISTURE", readSoilMoisture(), "raw", idx);
  } else if (activeSensor == "SOIL_TEMP") {
    sendReading("SOIL_TEMP", readSoilTemp(), "C", idx);
  } else if (activeSensor == "LIGHT") {
    sendReading("LIGHT", readLight(), "raw", idx);
  } else if (activeSensor == "EC") {
    sendReading("EC", readEC(), "mS/cm", idx);
  } else if (activeSensor == "PH") {
    sendReading("PH", readPH(), "pH", idx);
  }
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);

  BLEDevice::init("ESP32_SoilSensorNode");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService *service = server->createService(SERVICE_UUID);

  BLECharacteristic *cmdChar = service->createCharacteristic(
      COMMAND_CHAR_UUID, BLECharacteristic::PROPERTY_WRITE);
  cmdChar->setCallbacks(new CommandCallbacks());

  dataChar = service->createCharacteristic(
      DATA_CHAR_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  dataChar->addDescriptor(new BLE2902());

  service->start();

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.println("BLE advertising started, waiting for connection...");
}

void loop() {
  unsigned long now = millis();

  switch (state) {
    case IDLE:
      // nothing to do, waiting for a command
      break;

    case STABILIZING:
      if (now - stateStartMillis >= STABILIZE_MS) {
        state = READING;
        stateStartMillis = now;
        readingIndex = 1;
        takeReadingAndSend(readingIndex);
      }
      break;

    case READING:
      if (now - stateStartMillis >= READING_GAP_MS) {
        readingIndex++;
        stateStartMillis = now;
        if (readingIndex > TOTAL_READINGS) {
          // cycle complete, back to idle, ready for next sensor command
          state = IDLE;
          activeSensor = "";
        } else {
          takeReadingAndSend(readingIndex);
        }
      }
      break;
  }
}
