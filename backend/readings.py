import sqlite3
from config import DB_PATH
from rule_engine import get_solutions, build_farmer_report

# STORES MAXIMUM VALUES
calibrated_values = {
    "soil_temp" : {
        "cool" : 20,
        "warm" : 32,
        # hot : > 32
    },
    "soil_moist" : {
        "dry": 2400,
        "moist": 1900,
        "saturated": 1500
        # waterlogged : below 1500
    },
    "light" : {
        "cloudy" : 1200,
        "partly cloudy" : 2800
        # sunny : above 2800
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
    elif soil_moist > word_data["soil_moist"]["dry"]:
        soil_moist_label = "dry"
    elif soil_moist > word_data["soil_moist"]["moist"]:
        soil_moist_label = "moist"
    elif soil_moist > word_data["soil_moist"]["saturated"]:
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



def new_session(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM readings_raw")
    conn.commit()
    conn.close()


def send_reading(pending_id, db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Step 1: fetch the pending row
    cur.execute("SELECT * FROM readings_pending WHERE id = ?", (pending_id,))
    columns = [d[0] for d in cur.description]
    row = cur.fetchone()

    if row is None:
        conn.close()
        return False

    pending_row = dict(zip(columns, row))

    # Step 2: run the rule engine
    reasons = get_solutions(pending_row)

    # Crop not selected or no threshold data: keep the reading in pending
    if reasons is None:
        conn.close()
        return False

    report = build_farmer_report(reasons)

    # Step 3: set status (good / caution / problem)
    status = "good"
    for r in reasons:
        if "ideal" in r:
            if status == "good":
                status = "caution"
        else:
            status = "problem"

    # Step 4: copy to history, then delete from pending (one transaction)
    try:
        cur.execute("""
            INSERT INTO readings_history
            (crop_stage_id, recommendation, status, ph, ec, soil_temp, soil_moist,
             air_temp, air_moist, light, k, n, p, lat, long, plot_id,
             timestamp, source_device)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pending_row["crop_stage_id"], report, status,
              pending_row["ph"], pending_row["ec"],
              pending_row["soil_temp"], pending_row["soil_moist"],
              pending_row["air_temp"], pending_row["air_moist"],
              pending_row["light"],
              pending_row["k"], pending_row["n"], pending_row["p"],
              pending_row["lat"], pending_row["long"], pending_row["plot_id"],
              pending_row["timestamp"], pending_row["source_device"]))

        cur.execute("DELETE FROM readings_pending WHERE id = ?", (pending_id,))
        conn.commit()
        result = True
    except Exception:
        conn.rollback()
        result = False

    conn.close()
    return result