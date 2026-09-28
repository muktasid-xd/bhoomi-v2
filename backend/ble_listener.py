import asyncio
import json
import sqlite3
from datetime import datetime

from bleak import BleakScanner, BleakClient

from config import DB_PATH
from readings import new_session

DEVICE_NAME = "Bhoomi_Probe"
CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
TOTAL_READINGS = 15
SCAN_TIMEOUT = 30
WAIT_TIMEOUT = 150

# JSON key from the ESP32 -> readings_raw column
KEY_MAP = {
    "device": "device_name",
    "dht11_temperature": "air_temp",
    "humidity": "air_moist",
    "ds18b20_temperature": "soil_temp",
    "light": "light",
    "soil_moisture": "soil_moist",
    "ec": "ec",
    "ph": "ph"
}

# state is one of: idle, searching, warming, reading, done, failed
status = {
    "state": "idle",
    "saved": 0,
    "total": TOTAL_READINGS,
    "message": ""
}

done_event = None


def set_status(state, message = ""):
    status["state"] = state
    status["message"] = message


def get_status():
    return dict(status)


def is_running():
    return status["state"] in ("searching", "warming", "reading")


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

    # The ESP32 has no clock, so the timestamp is added here
    packet["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return packet


def save_to_raw(packet, db_path = DB_PATH):
    columns = list(packet.keys())
    values = []
    for column in columns:
        values.append(packet[column])

    column_text = ", ".join(columns)
    marks = ", ".join(["?"] * len(columns))
    sql = "INSERT INTO readings_raw (" + column_text + ") VALUES (" + marks + ")"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    conn.close()


def on_notify(sender, data):
    if status["saved"] >= TOTAL_READINGS:
        return

    packet = parse_packet(data)
    if packet is None:
        return

    save_to_raw(packet)
    status["saved"] = status["saved"] + 1
    set_status("reading", "Reading " + str(status["saved"]) + " of " + str(TOTAL_READINGS))
    print("Saved reading", status["saved"], "of", TOTAL_READINGS, packet)

    if status["saved"] >= TOTAL_READINGS:
        done_event.set()

def on_disconnect(client):
    if done_event is not None:
        done_event.set()


async def run_listener():
    global done_event
    done_event = asyncio.Event()

    set_status("searching", "Looking for the probe...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=SCAN_TIMEOUT)
    if device is None:
        set_status("failed", "Probe not found. Check that it is powered on.")
        return

    async with BleakClient(device, disconnected_callback=on_disconnect) as client:
        set_status("warming", "Connected. Probe is warming up (about 60 seconds).")
        await client.start_notify(CHAR_UUID, on_notify)

        try:
            await asyncio.wait_for(done_event.wait(), timeout=WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            pass

        try:
            await client.stop_notify(CHAR_UUID)
        except Exception:
            pass

    if status["saved"] >= TOTAL_READINGS:
        set_status("done", "All " + str(TOTAL_READINGS) + " readings saved.")
    else:
        set_status("failed", "Timed out. Got " + str(status["saved"]) + " readings.")


def run_session():
    # Blocking. The API will call this inside a background thread.
    if is_running():
        return False

    set_status("searching", "Starting...")
    status["saved"] = 0
    new_session()
    
    try:
        asyncio.run(run_listener())
    except Exception as e:
        set_status("failed", "Bluetooth error: " + str(e))
        return False

    return status["state"] == "done"



if __name__ == "__main__":
    run_session()
    print(get_status())
    