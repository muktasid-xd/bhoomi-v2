import sqlite3
from config import DB_PATH, SENSOR_DB_PATH

# crop_stages, crop_thresholds, universal_solution, crop_solution, crop_factors  
def create_database(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    # CROPS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crop_stages (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            variety TEXT NOT NULL,
            stage TEXT NOT NULL,
            UNIQUE(name, variety, stage)
        );
    """)
    
    # CROP THRESHOLDS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crop_thresholds (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER NOT NULL REFERENCES crop_stages(id),
            ph_low REAL, ph_high REAL,
            ec_low REAL, ec_high REAL,
            soil_moist TEXT,
            soil_temp TEXT,
            air_moist_low REAL, air_moist_high REAL,
            air_temp_low REAL, air_temp_high REAL,
            n_low REAL, n_high REAL,
            p_low REAL, p_high REAL,
            k_low REAL, k_high REAL,
            light TEXT,
            UNIQUE(crop_stage_id)
        );
    """)
    
    # UNIVERSAL CROP SOLUTION
    cur.execute("""
        CREATE TABLE IF NOT EXISTS universal_solution (
            id INTEGER PRIMARY KEY,
            parameter TEXT NOT NULL,
            state TEXT NOT NULL,
            advice TEXT NOT NULL,
            UNIQUE(parameter, state)
        );
    """)
    
    # CROP SPECIFIC SOLUTION
    cur.execute ("""
        CREATE TABLE IF NOT EXISTS crop_solution (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER NOT NULL REFERENCES crop_stages(id),
            parameter TEXT NOT NULL,
            points_to TEXT NOT NULL,
            UNIQUE(crop_stage_id, parameter, trigger_state)
        );
    """)
    
    # SOLUTION FACTORS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS solution_factors (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER NOT NULL REFERENCES crop_stages(id),
            n_factor REAL,
            p_factor REAL,
            k_factor REAL,
            ph_low_factor REAL,
            ph_high_factor REAL,
            UNIQUE(crop_stage_id)
        );
    """)
    
    conn.commit()
    conn.close()
    print(f"Database created at {db_path}")

def create_sensor_readings(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_sensor_readings (
            id INTEGER PRIMARY KEY,
            device_name TEXT,
            timestamp TEXT,
            ec REAL,
            ph REAL,
            air_moist REAL,
            air_temp REAL,
            soil_moist REAL,
            soil_temp REAL,
            light REAL
        );
    """)

def create_pending_readings(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_readings (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER REFERENCES crop_stages(id),
            ph REAL,
            ec REAL,
            soil_temp TEXT,
            soil_moist TEXT,
            air_temp REAL,
            air_moist REAL,
            light REAL,
            k REAL,
            n REAL,
            p REAL,
            lat REAL,
            long REAL,
            plot_id INTEGER,
            timestamp TEXT,
            status TEXT,
            source_device TEXT
        );
    """)

if __name__ == "__main__":
    create_database()
    create_sensor_readings()
    create_pending_readings()

