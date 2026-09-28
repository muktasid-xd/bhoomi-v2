import sqlite3
from config import DB_PATH

PARAMETER_NAMES = {
    "ph": "pH",
    "ec": "EC",
    "n": "Nitrogen (N)",
    "p": "Phosphorus (P)",
    "k": "Potassium (K)",
    "soil_temp": "Soil temperature",
    "soil_moist": "Soil moisture",
    "air_temp": "Air temperature",
    "air_moist": "Air humidity",
    "light": "Light"
}

# Placeholder units: change these to your real ones
UNITS = {
    "ph": "kg/ha",
    "n": "kg/ha",
    "p": "kg/ha",
    "k": "kg/ha"
}

# Column names in crop_solution that hold a solution
SOLUTION_COLUMNS = [
    "ph_low", "ph_high",
    "ec_low", "ec_high",
    "n_low", "n_high",
    "p_low", "p_high",
    "k_low", "k_high",
    "soil_moist_dry", "soil_moist_moist", "soil_moist_saturated", "soil_moist_waterlogged",
    "soil_temp_cool", "soil_temp_warm", "soil_temp_hot"
]

NUMERIC_PARAMETERS = ["ph", "ec", "n", "p", "k"]
WORDS_PARAMETERS = ["soil_temp", "soil_moist"]
NON_FIXABLE_PARAMETERS = ["air_temp", "air_moist", "light"]
MEASURABLE_PARAMETERS = ["ph", "n", "p", "k"]


def get_threshold_row(crop_info_id, db_path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM crop_thresholds WHERE crop_info_id = ?", (crop_info_id,)
    )

    columns = [d[0] for d in cur.description]
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(zip(columns, row))


def check_numeric(param, value, threshold_dict):
    if value is None:
        return None

    low = threshold_dict[param + "_low"]
    high = threshold_dict[param + "_high"]

    if low is None or high is None:
        return None

    if value < low:
        return param + "_low"
    if value > high:
        return param + "_high"
    return "healthy"


def check_word(param, value, threshold_dict):
    if value is None:
        return None

    if value == threshold_dict[param]:
        return "healthy"

    # returns full flag name, e.g. soil_moist_waterlogged
    return param + "_" + value


def check_nonfixable(param, value, threshold_dict):
    if value is None:
        return None

    if param in ("air_temp", "air_moist"):
        low = threshold_dict[param + "_low"]
        high = threshold_dict[param + "_high"]

        if low is None or high is None:
            return None

        if value < low:
            return param + "_low"
        if value > high:
            return param + "_high"
        return "healthy"

    # light (text value)
    if value == threshold_dict["light"]:
        return "healthy"
    return param + "_" + value


def get_solution(crop_info_id, flag_name, db_path = DB_PATH):
    # Column names cannot be passed as ?, so only allow known names
    if flag_name not in SOLUTION_COLUMNS:
        return None

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        f"SELECT {flag_name} FROM crop_solution WHERE crop_info_id = ?", (crop_info_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    solution = row[0]
    if solution is None or solution == "no solution required":
        return None

    return solution


def get_factor(crop_info_id, param, flag_name, db_path = DB_PATH):
    if param == "ph":
        if flag_name == "ph_low":
            column = "ph_high_factor"
        else:
            column = "ph_low_factor"
    else:
        column = param + "_factor"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        f"SELECT {column} FROM factor_data WHERE crop_info_id = ?", (crop_info_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return row[0]


def calc_dosage(value, threshold_value, factor):
    if factor is None or threshold_value is None:
        return None

    deficit = abs(value - threshold_value)
    return factor * deficit


def build_reason(param, flag_name, value, threshold_dict, crop_info_id, reasons):
    solution = get_solution(crop_info_id, flag_name)

    dosage = None
    if param in MEASURABLE_PARAMETERS:
        if flag_name.endswith("_low"):
            threshold_value = threshold_dict[param + "_low"]
        else:
            threshold_value = threshold_dict[param + "_high"]

        factor = get_factor(crop_info_id, param, flag_name)
        dosage = calc_dosage(value, threshold_value, factor)

    reasons.append(
        {
            "parameter": param,
            "flag": flag_name,
            "solution": solution,
            "dosage": dosage
        }
    )


def build_nonfixable_reason(param, flag_name, threshold_dict, reasons):
    if param in ("air_temp", "air_moist"):
        ideal = f"{threshold_dict[param + '_low']} - {threshold_dict[param + '_high']}"
    else:
        ideal = threshold_dict["light"]

    reasons.append(
        {
            "parameter": param,
            "flag": flag_name,
            "solution": None,
            "dosage": None,
            "ideal": ideal
        }
    )


def get_solutions(pending_row):
    crop_info_id = pending_row["crop_stage_id"]
    threshold_row = get_threshold_row(crop_info_id)

    if threshold_row is None:
        return None

    reasons = []

    for param in NUMERIC_PARAMETERS:
        flag_name = check_numeric(param, pending_row[param], threshold_row)
        if flag_name is not None and flag_name != "healthy":
            build_reason(param, flag_name, pending_row[param], threshold_row, crop_info_id, reasons)

    for param in WORDS_PARAMETERS:
        flag_name = check_word(param, pending_row[param], threshold_row)
        if flag_name is not None and flag_name != "healthy":
            build_reason(param, flag_name, pending_row[param], threshold_row, crop_info_id, reasons)

    for param in NON_FIXABLE_PARAMETERS:
        flag_name = check_nonfixable(param, pending_row[param], threshold_row)
        if flag_name is not None and flag_name != "healthy":
            build_nonfixable_reason(param, flag_name, threshold_row, reasons)

    return reasons


def build_farmer_report(reasons):
    if reasons is None:
        return "Crop details not found. Please select the crop and stage."

    if len(reasons) == 0:
        return "All readings are within the healthy range for this crop and stage."

    lines = []
    number = 1

    for r in reasons:
        param = r["parameter"]
        state = r["flag"][len(param) + 1:]
        name = PARAMETER_NAMES[param] + " is " + state

        if "ideal" in r:
            line = f"{number}. {name}: outside ideal range (ideal: {r['ideal']}). Not something you can fix."
        elif r["solution"] is None:
            line = f"{number}. {name}: no solution found in database."
        elif r["dosage"] is not None:
            amount = str(round(r["dosage"], 2)) + " " + UNITS[param]
            line = f"{number}. {name}: {r['solution']}. Amount: {amount}"
        else:
            line = f"{number}. {name}: {r['solution']}"

        lines.append(line)
        number = number + 1

    return "\n".join(lines)

def build_technical_reason(reason):
    text = f"{reason['parameter']}: {reason['flag']}"
    if reason["dosage"] is not None:
        text += f" (amount: {reason['dosage']})"
    return text


def get_farmer_report(pending_row):
    reasons = get_solutions(pending_row)
    return build_farmer_report(reasons)