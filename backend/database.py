import sqlite3
import os
from datetime import datetime, timezone
from config import DB_PATH

# Establishes a connection to the SQLite database file.
# Creates the destination folder automatically if it doesn't exist,
# and configures rows to be accessible using column names (like a Python dictionary).
def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initializes the database layout (schema) when the application starts.
# Creates two tables if they don't already exist:
# 1. 'pending_readings' to hold raw, 50-sample filtered sensor data.
# 2. 'ai_reviewed_records' to hold finalized records processed by Gemini AI.
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
            soil_type TEXT,
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
            ai_summary TEXT,
            ai_recommended_action TEXT,
            ai_urgency TEXT,
            analysis_source TEXT
        )
        """
    )

    conn.commit()
    conn.close()

# ---------------------------
# DATABSE 1
# ---------------------------

# Saves a newly averaged 50-sample sensor packet into 'pending_readings'.
# Automatically records a UTC timestamp, inserts optional GPS coordinates,
# safely extracts each sensor metric, commits the record, and returns the newly generated row ID.
def insert_pending_reading(averaged: dict, lat=None, lon=None) -> int:
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO pending_readings (
            timestamp, latitude, longitude, moisture_percent, ph, ec,
            soil_temp_c, air_temp_c, air_humidity_percent,
            light_percent, soil_type, crop, origin, status 
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            datetime.now(timezone.utc).isoformat(),
            lat,
            lon,
            averaged.get("moisture_percent"),
            averaged.get("ph"),
            averaged.get("ec"),
            averaged.get("soil_temp_c"),
            averaged.get("air_temp_c"),
            averaged.get("air_humidity_percent"),
            averaged.get("light_percent"),
            averaged.get("soil_type"),
            None,
            "local",
            "pending",
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id

# Saves a sensor data packet received over LAN (Wi-Fi) into your local database.
#
# HOW IT WORKS:
# 1. Takes an 'entry' dictionary sent from another device on the network.
# 2. Uses the sender's original timestamp (or creates a UTC timestamp if missing).
# 3. Keeps the sender's GPS coordinates, sensor metrics, and crop selection.
# 4. Tags the record's origin as 'shared' and status as 'pending' for future AI review.
# 5. Returns the newly assigned local row ID (e.g., 1, 2, 3...).
#
# USAGE EXAMPLE:
# incoming_packet = {
#     "moisture_percent": 38.5, "ph": 6.8, "ec": 1.2,
#     "soil_temp_c": 27.4, "air_temp_c": 31.0, "soil_type": "Laterite",
#     "crop": "Mango", "latitude": 16.99, "longitude": 73.31
# }
# record_id = insert_shared_reading(incoming_packet)
def insert_shared_reading(entry: dict) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pending_readings (
            timestamp, latitude, longitude, moisture_percent, ph, ec,
            soil_temp_c, air_temp_c, air_humidity_percent,
            light_percent, soil_type, crop, origin, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            entry.get("latitude"),
            entry.get("longitude"),
            entry.get("moisture_percent"),
            entry.get("ph"),
            entry.get("ec"),
            entry.get("soil_temp_c"),
            entry.get("air_temp_c"),
            entry.get("air_humidity_percent"),
            entry.get("light_percent"),
            entry.get("soil_type"),
            entry.get("crop"),
            "shared",
            "pending",
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return new_id


# Fetches all unreviewed sensor readings from 'pending_readings' (newest first)
# and converts each database row into a dictionary for Gemini AI processing.
def list_pending_readings():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM pending_readings WHERE status = 'pending' ORDER BY id DESC"
    )

    rows = []
    for row in cur.fetchall():  #cur.fetchall() --> row rows
        rows.append(dict(row))

    conn.close()
    return rows


# Fetches a single sensor reading from 'pending_readings' using its unique ID.
#
# PARAMETERS:
#   reading_id (int): The unique database row ID to search for.
#
# RETURNS:
#   dict: A dictionary of sensor metrics if the record exists.
#   None: If no record is found with the given ID (prevents runtime crashes).
def get_pending_readings(reading_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM pending_readings WHERE id = ?", (reading_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is not None:
        return dict(row)
    else:
        return None


# Permanently removes a reading from 'pending_readings' by its ID.
# Use this after a record is successfully processed or no longer needed.
def hard_delete_pending_readings(reading_id: int):
    """Fully remove a row after successfully sending it to AI"""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM pending_readings WHERE id = ?", (reading_id,)
    )
    conn.commit()
    conn.close()


# Updates the processing status (e.g., 'reviewed', 'error') of a pending reading.
# Uses parameterized queries to safely set status by reading_id and commits changes.
def mark_pending_status(reading_id: int, status: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE pending_readings SET status = ? WHERE id = ?",
        (status, reading_id),
    )
    conn.commit()
    conn.close()

# Assigns or updates the crop type for an unreviewed reading in 'pending_readings'.
# Used when raw sensor data is initially saved without a crop ('unidentified')
# so AI has the correct crop context during AI analysis.
def update_pending_crop(reading_id: int, crop: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE pending_readings SET crop = ? WHERE id = ?",
        (crop, reading_id),
    )
    conn.commit()
    conn.close()