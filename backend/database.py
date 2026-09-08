import sqlite3
import os
from datetime import datetime, timezone
from config import DB_PATH

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            moisture_percent REAL,
            ph REAL,
            ec REAL,
            soil_temp_c REAL,
            air_temp_c REAL,
            air_humidity_percent REAL,
            light_percent REAL,
            soil_type REAL,
            crop TEXT,
            origin TEXT DEFAULT 'local',
            status TEXT DEFAULT 'pending'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_reviewed_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            crop TEXT,
            moisture_percent REAL,
            ph REAL,
            ec REAL,
            soil_temp_c REAL,
            air_temp_c REAL,
            air_humidity_percent REAL,
            light_percent REAL,
            soil_type TEXT,
            air_summary TEXT,
            ai_recommend_action TEXT,
            ai_urgency TEXT,
            analysis_source TEXT
        )
        """
    )

    conn.commit()
    conn.close()