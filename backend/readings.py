import sqlite3
from config import DB_PATH

# STORES MAXIMUM VALUES
calibrated_values = {
    "soil_temp" : {

        "cool" : 20,
        "warm" : 32,
        # hot : > 32
    },
    "soil_moist" : {

        "dry": 20,
        "moist": 50,
        "saturated": 80
        # waterlogged : > 80
    },
    "light" : {
        "cloudy" : 30,
        "partly cloudy" : 70
        # sunny : > 70
    }
}

def save_readings(db_path = DB_PATH, word_data = calibrated_values):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        UPDATE readings_raw
        SET lat = NULL, long = NULL
        WHERE lat IS NULL OR long IS NULL
        OR lat < -90 OR lat > 90
        OR long < -180 OR long > 180
        OR (lat = 0 AND long = 0)
    """)

    cur.execute("""
        SELECT 
            AVG(ph),
            AVG(ec),
            AVG(soil_temp), 
            AVG(soil_moist), 
            AVG(air_temp), 
            AVG(air_moist), 
            AVG(light),
            AVG(lat),
            AVG(long),
        MAX(timestamp), MAX(device_name), COUNT(*)
        from readings_raw
    """)
    row = cur.fetchone()

    if row[11] == 0:
        conn.close()
        return False

    soil_temp = row[2]
    if soil_temp is None:
        soil_temp_label = None
    elif soil_temp < word_data["soil_temp"]["cool"]:
        soil_temp_label = "cool"
    elif soil_temp < word_data["soil_temp"]["warm"]:
        soil_temp_label = "warm"
    else:
        soil_temp_label = "hot"

    soil_moist = row[3]
    if soil_moist is None:
        soil_moist_label = None
    elif soil_moist < word_data["soil_moist"]["dry"]:
        soil_moist_label = "dry"
    elif soil_moist < word_data["soil_moist"]["moist"]:
        soil_moist_label = "moist"
    elif soil_moist < word_data["soil_moist"]["saturated"]:
        soil_moist_label = "saturated"
    else:
        soil_moist_label = "waterlogged"

    light = row[6]
    if light is None:
        light_label = None
    elif light < word_data["light"]["cloudy"]:
        light_label = "cloudy"
    elif light < word_data["light"]["partly cloudy"]:
        light_label = "partly cloudy"
    else:
        light_label = "sunny"

    try:
        cur.execute("""
            INSERT INTO readings_pending
            (ph, ec, soil_temp, soil_moist, air_temp, air_moist, light,
             lat, long, timestamp, status, source_device)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (row[0], row[1], soil_temp_label, soil_moist_label,
              row[4], row[5], light_label,
              row[7], row[8], row[9], "pending", row[10]))
        conn.commit()
        result = True
    except Exception:
        conn.rollback()
        result = False

    conn.close()
    return result    