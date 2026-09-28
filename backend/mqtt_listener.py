import json
import paho.mqtt.client as mqtt

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "college_iot_esp32/sensors"

# JSON key from the ESP32 -> readings_raw column
# Update this when the real packet format is known
KEY_MAP = {
    "device": "device_name",
    "timestamp": "timestamp",
    "dht11_temperature": "air_temp",
    "humidity": "air_moist",
    "ds18b20_temperature": "soil_temp",
    "light": "light",
    "soil_moisture": "soil_moist",
    "ec": "ec",
    "ph": "ph"
}

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to MQTT broker, code:", reason_code)
    client.subscribe(MQTT_TOPIC)

def parse_packet(payload):
    try:
        data = json.loads(payload.decode())
    except Exception as e:
        print("Bad JSON:", e)
        return None

    if not isinstance(data, dict):
        print("Packet is not a JSON object:", data)
        return None

    packet = {}
    for json_key in KEY_MAP:
        column = KEY_MAP[json_key]
        packet[column] = data.get(json_key)
    return packet

def on_message(client, userdata, msg):
    packet = parse_packet(msg.payload)
    if packet is None:
        return

    # Cleaning and saving to readings_raw will be added here later
    print("Fetched packet:", packet)

def start_listener():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    start_listener()