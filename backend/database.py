import sqlite3
from config import DB_PATH

# CROPS
# CROP THRESHOLDS
# SOLUTION
# NPK FACTORS
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
            trigger_state TEXT NOT NULL,
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
    
if __name__ == "__main__":
    create_database()

