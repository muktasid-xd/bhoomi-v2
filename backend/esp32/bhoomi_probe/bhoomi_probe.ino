#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define DS18B20_PIN 5
#define DHT_PIN 18
#define SOIL_PIN 34
#define LDR_PIN 35
#define LCD_ADDRESS 0x27

#define DEVICE_NAME "Bhoomi_Probe"
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

#define WARMUP_SECONDS 60
#define TOTAL_READINGS 15
#define GAP_MS 3000

DHT dht(DHT_PIN, DHT11);
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);
LiquidCrystal_I2C lcd(LCD_ADDRESS, 16, 2);

BLECharacteristic *dataChar;
volatile bool deviceConnected = false;
BLEServer *bleServer;
uint16_t connId = 0;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server, esp_ble_gatts_cb_param_t *param) {
    deviceConnected = true;
    connId = param->connect.conn_id;
  }
  void onDisconnect(BLEServer *server) {
    deviceConnected = false;
    BLEDevice::startAdvertising();
  }
};

void showLcd(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

String numberOrNull(float value) {
  if (isnan(value)) {
    return "null";
  }
  return String(value, 1);
}

void sendOneReading(int number) {
  float airTemp = dht.readTemperature();
  float airMoist = dht.readHumidity();

  pinMode(DS18B20_PIN, INPUT_PULLUP);

  ds18b20.requestTemperatures();
  float soilTemp = ds18b20.getTempCByIndex(0);
  if (soilTemp == DEVICE_DISCONNECTED_C) {
    soilTemp = NAN;
  }

  int soilMoist = analogRead(SOIL_PIN);
  int light = analogRead(LDR_PIN);

  String packet = "{";
  packet += "\"device\":\"" + String(DEVICE_NAME) + "\",";
  packet += "\"dht11_temperature\":" + numberOrNull(airTemp) + ",";
  packet += "\"humidity\":" + numberOrNull(airMoist) + ",";
  packet += "\"ds18b20_temperature\":" + numberOrNull(soilTemp) + ",";
  packet += "\"light\":" + String(light) + ",";
  packet += "\"soil_moisture\":" + String(soilMoist);
  packet += "}";

  dataChar->setValue(packet.c_str());
  dataChar->notify();
  Serial.println(packet);

  showLcd("Reading " + String(number) + "/" + String(TOTAL_READINGS),
          "S:" + numberOrNull(soilTemp) + " M:" + String(soilMoist));
}

void setup() {
  Serial.begin(115200);

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  showLcd("Bhoomi Probe", "Starting...");

  dht.begin();
  ds18b20.begin();
  pinMode(DS18B20_PIN, INPUT_PULLUP);
  analogReadResolution(12);

  BLEDevice::init(DEVICE_NAME);
  BLEDevice::setMTU(247);
  BLEServer *server = BLEDevice::createServer();
  bleServer = server;
  server->setCallbacks(new ServerCallbacks());

  BLEService *service = server->createService(SERVICE_UUID);
  dataChar = service->createCharacteristic(CHAR_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  dataChar->addDescriptor(new BLE2902());
  service->start();

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  BLEDevice::startAdvertising();

}

void loop() {
  Serial.println("Waiting for PC to connect...");
  showLcd("Ready. Waiting", "for PC (BLE)");
  while (!deviceConnected) {
    delay(200);
  }

  Serial.println("Warming up for 60 seconds...");
  for (int s = WARMUP_SECONDS; s > 0; s--) {
    showLcd("Warming up...", "Wait " + String(s) + " sec");
    delay(1000);
    if (!deviceConnected) {
      return;
    }
  }

  for (int i = 1; i <= TOTAL_READINGS; i++) {
    if (!deviceConnected) {
      return;
    }
    sendOneReading(i);
    delay(GAP_MS);
  }

  Serial.println("Session done.");
  showLcd("Done", "Session complete");

  delay(2000);
  bleServer->disconnect(connId);
  delay(2000);
  deviceConnected = false;
  BLEDevice::startAdvertising();
  delay(500);
}