"""
Minimal backend for the ESP32 BLE sensor prototype.

Responsibilities (intentionally thin):
  - POST /session/new   -> starts a new session, returns session_id
  - POST /reading        -> receives one JSON reading (already built by ESP32,
                             forwarded as-is by the frontend), stamps real-world
                             timestamp, inserts a row into SQLite. No validation,
                             no unit conversion, no sensor-name mapping.
  - GET  /readings       -> (debug helper) list all rows, newest first

Run:
    pip install flask
    python backend.py
Server listens on http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_cors import CORS  # pip install flask-cors (browser fetch needs this)
import sqlite3
import uuid
from datetime import datetime

DB_PATH = "sensor_data.db"

app = Flask(__name__)
CORS(app)  # allow the local HTML file / browser to call this API

current_session_id = None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sensor_name TEXT,
            reading_index INTEGER,
            value REAL,
            unit TEXT,
            timestamp TEXT
        )
        """
    )
    return conn


@app.route("/session/new", methods=["POST"])
def new_session():
    global current_session_id
    current_session_id = str(uuid.uuid4())
    return jsonify({"session_id": current_session_id})


@app.route("/reading", methods=["POST"])
def add_reading():
    global current_session_id
    data = request.get_json(force=True)

    sensor_name = data.get("sensor")
    value = data.get("value")  # may be None -> stored as NULL
    unit = data.get("unit")
    reading_index = data.get("reading_index")
    timestamp = datetime.now().isoformat(timespec="seconds")  # real-world time

    conn = get_db()
    conn.execute(
        "INSERT INTO readings (session_id, sensor_name, reading_index, value, unit, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (current_session_id, sensor_name, reading_index, value, unit, timestamp),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "session_id": current_session_id, "timestamp": timestamp})


@app.route("/readings", methods=["GET"])
def list_readings():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, session_id, sensor_name, reading_index, value, unit, timestamp "
        "FROM readings ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    cols = ["id", "session_id", "sensor_name", "reading_index", "value", "unit", "timestamp"]
    return jsonify([dict(zip(cols, r)) for r in rows])


if __name__ == "__main__":
    get_db().close()  # ensure table exists on startup
    app.run(host="0.0.0.0", port=5000, debug=True)