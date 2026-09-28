from config import DB_PATH
import sqlite3


def create_id_table(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS id_info (
            id INTEGER PRIMARY KEY,
            crop TEXT,
            stage TEXT,
            state TEXT,
            region TEXT,
            variety TEXT
        );
    """)

    conn.commit()
    conn.close()


def create_readings_database (db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings_raw (
            id INTEGER PRIMARY KEY,
            device_name TEXT,
            timestamp TEXT,
            ec REAL,
            ph REAL,
            air_moist REAL,
            air_temp REAL,
            soil_moist REAL,
            soil_temp REAL,
            light REAL,
            lat REAL,
            long REAL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings_pending (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER REFERENCES id_info(id),
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

    conn.commit()
    conn.close()


def create_solution_database(db_path = DB_PATH) :
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS crop_thresholds (
            id INTEGER PRIMARY KEY,
            crop_info_id INTEGER REFERENCES id_info(id),
            ph_low REAL, ph_high REAL,
            ec_low REAL, ec_high REAL,
            air_moist_low REAL, air_moist_high REAL,
            air_temp_low REAL, air_temp_high REAL,
            n_low REAL, n_high REAL,
            p_low REAL, p_high REAL,
            k_low REAL, k_high REAL,
            soil_moist TEXT, soil_temp TEXT,
            light TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS crop_solution (
            id INTEGER PRIMARY KEY,
            crop_info_id INTEGER REFERENCES id_info(id),
            ph_low TEXT, ph_high TEXT,
            ec_low TEXT, ec_high TEXT,
            n_low TEXT, n_high TEXT,
            p_low TEXT, p_high TEXT,
            k_low TEXT, k_high TEXT,
            soil_moist_dry TEXT, soil_moist_moist TEXT, soil_moist_saturated TEXT, soil_moist_waterlogged TEXT, 
            soil_temp_cool TEXT, soil_temp_warm TEXT, soil_temp_hot TEXT,
            light TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS factor_data (
            id INTEGER PRIMARY KEY,
            crop_info_id INTEGER REFERENCES id_info(id),
            ph_high_factor REAL,
            ph_low_factor REAL,
            n_factor REAL,
            p_factor REAL,
            k_factor REAL
        );
    """)

    conn.commit()
    conn.close()

def create_readings_history(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings_history (
            id INTEGER PRIMARY KEY,
            crop_stage_id INTEGER REFERENCES id_info(id),
            recommendation TEXT,
            status TEXT,
            ph REAL,
            ec REAL,
            soil_temp TEXT,
            soil_moist TEXT,
            air_temp REAL,
            air_moist REAL,
            light TEXT,
            k REAL,
            n REAL,
            p REAL,
            lat REAL,
            long REAL,
            plot_id INTEGER,
            timestamp TEXT,
            source_device TEXT
        );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_id_table()
    create_readings_database()
    create_solution_database()
    create_readings_history()