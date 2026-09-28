import sqlite3
from datetime import datetime
from config import DB_PATH

NUMBER_COLUMNS = ["ph", "ec", "air_temp", "air_moist", "k", "n", "p", "lat", "long"]

LABEL_COLUMNS = {
    "soil_temp": ["cool", "warm", "hot"],
    "soil_moist": ["dry", "moist", "saturated", "waterlogged"],
    "light": ["cloudy", "partly cloudy", "sunny"]
}

NON_NEGATIVE = ["ph", "ec", "air_moist", "k", "n", "p"]


def clean_value(column, value, db_path = DB_PATH):
    # Returns (True, cleaned_value) or (False, error_message)
    if value == "":
        value = None

    if column in NUMBER_COLUMNS:
        if value is None:
            return True, None
        try:
            number = float(value)
        except (ValueError, TypeError):
            return False, column + " must be a number"

        if column in NON_NEGATIVE and number < 0:
            return False, column + " cannot be negative"
        if column == "ph" and number > 14:
            return False, "ph cannot be above 14"
        if column == "air_moist" and number > 100:
            return False, "air_moist cannot be above 100"
        return True, number

    if column in LABEL_COLUMNS:
        if value is None:
            return True, None
        if value not in LABEL_COLUMNS[column]:
            return False, column + " must be one of " + ", ".join(LABEL_COLUMNS[column])
        return True, value

    if column == "crop_stage_id":
        if value is None:
            return True, None
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id FROM id_info WHERE id = ?", (value,))
        found = cur.fetchone()
        conn.close()
        if found is None:
            return False, "crop_stage_id not found in id_info"
        return True, int(value)

    if column == "plot_id":
        if value is None:
            return True, None
        try:
            return True, int(value)
        except (ValueError, TypeError):
            return False, "plot_id must be a whole number"

    return False, column + " cannot be edited"


def get_pending_list(db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*, i.crop, i.stage
        FROM readings_pending p
        LEFT JOIN id_info i ON p.crop_stage_id = i.id
        ORDER BY p.id DESC
    """)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(dict(zip(columns, row)))
    return result


def get_pending(pending_id, db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*, i.crop, i.stage
        FROM readings_pending p
        LEFT JOIN id_info i ON p.crop_stage_id = i.id
        WHERE p.id = ?
    """, (pending_id,))
    columns = [d[0] for d in cur.description]
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None
    return dict(zip(columns, row))


def update_pending(pending_id, changes, db_path = DB_PATH):
    # changes is a dictionary, for example {"ph": 6.5, "soil_moist": "dry"}
    if len(changes) == 0:
        return False, "nothing to update"

    cleaned = {}
    for column in changes:
        ok, result = clean_value(column, changes[column], db_path)
        if not ok:
            return False, result
        cleaned[column] = result

    set_parts = []
    values = []
    for column in cleaned:
        set_parts.append(column + " = ?")
        values.append(cleaned[column])
    values.append(pending_id)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE readings_pending SET " + ", ".join(set_parts) + " WHERE id = ?",
        values
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()

    if changed == 0:
        return False, "reading not found"
    return True, "updated"


def add_manual_reading(values, db_path = DB_PATH):
    # values is a dictionary with any of the editable columns
    cleaned = {}
    for column in values:
        ok, result = clean_value(column, values[column], db_path)
        if not ok:
            return False, result
        cleaned[column] = result

    cleaned["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned["status"] = "pending"
    cleaned["source_device"] = "manual"

    columns = list(cleaned.keys())
    marks = ", ".join(["?"] * len(columns))
    column_text = ", ".join(columns)
    row_values = []
    for column in columns:
        row_values.append(cleaned[column])

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO readings_pending (" + column_text + ") VALUES (" + marks + ")",
        row_values
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return True, new_id


def delete_pending(pending_id, db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM readings_pending WHERE id = ?", (pending_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted > 0