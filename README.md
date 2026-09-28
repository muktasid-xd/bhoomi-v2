# 🌱 Bhoomi

Low-cost soil health monitoring for small-scale farmers in India.
A battery-powered ESP32 probe measures the soil, and a local web app turns the numbers into a plain-language recommendation: what is wrong with the soil and what to do about it.

Built by Team Eureka for Smart India Hackathon 2026.

## How it works

```
ESP32 probe --BLE--> Python backend --> Rule engine --> Farmer report
 (7 sensors)          (SQLite queue)    (crop thresholds
                                         + solutions)
```

1. **Connect:** press Start. The probe warms up for 60 seconds, then sends 15 readings.
2. **Queue:** the 15 readings are averaged into one reading. The farmer picks a crop and stage, and can edit values or add a manual reading.
3. **Soil Report:** the rule engine compares the reading with the crop's ideal ranges and returns fixes with dosages. Past reports are kept below it.

## Offline-first

- **No internet needed.** The probe talks to the computer over Bluetooth LE, and everything runs locally.
- **No cloud AI.** Diagnosis is fully rule-based, using a database of crop thresholds, solutions and dosage factors. Results are the same every time and never invented.
- **Local storage.** All data lives in one SQLite file (`data/bhoomi.db`).

## Hardware

| Part | Pin |
|---|---|
| DS18B20 soil temperature | D5 |
| DHT11 air temperature and humidity | D18 |
| Soil moisture sensor (analog) | D34 |
| LDR light module (analog) | D35 |
| 16x2 I2C LCD | SDA D21, SCL D22 |

pH and EC sensors are planned. The software already treats them as optional.

## Project structure

```
backend/    Flask API, BLE listener, rule engine, database code
frontend/   Single-page web app (HTML, CSS, JS)
data/       SQLite database
documents/  Circuit assembly
```

The ESP32 sketch lives in `backend/esp32/bhoomi_probe/`.

## Run it

**Requirements:** Python 3.10+, a Bluetooth adapter, and [arduino-cli](https://arduino.github.io/arduino-cli/) for flashing.

**1. Flash the probe (once)**
```powershell
arduino-cli core install esp32:esp32
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "OneWire" "DallasTemperature" "LiquidCrystal I2C"
cd backend
arduino-cli compile --fqbn esp32:esp32:esp32 esp32\bhoomi_probe
arduino-cli upload -p COM4 --fqbn esp32:esp32:esp32 esp32\bhoomi_probe
```
Change `COM4` to your port (`arduino-cli board list`).

**2. Start the app**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install flask flask-cors bleak
python api.py
```

**3. Open** http://127.0.0.1:5000

Power on the probe, wait for its screen to show **Ready. Waiting**, then press **Start New Session**.

## Notes

- Moisture and light cutoffs in `backend/readings.py` are placeholders. Calibrate them with your own dry/wet and dark/bright readings.
- Don't run `ble_listener.py` while `api.py` is running. The API starts the listener itself.

## Roadmap

- Farm Mode: farm map, plots and per-plot trend graphs
- pH and EC sensors
- Multilingual support (English, Hindi, Marathi)
- Local language model for phrasing (optional)