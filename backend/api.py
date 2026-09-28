import sqlite3
import threading

import os
import database
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import DB_PATH
from readings import save_readings, new_session, send_reading
import ble_listener
import queue_manager

app = Flask(__name__)
CORS(app)
FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


@app.route("/")
def home():
    return send_from_directory(FRONTEND, "index.html")


def run_query(sql, params = ()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql, params)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(dict(zip(columns, row)))
    return result


def error(message, code = 400):
    return jsonify({"ok": False, "message": message}), code


# ---------- Session (Connect page) ----------

@app.route("/session/start", methods=["POST"])
def session_start():
    if ble_listener.is_running():
        return error("A session is already running")

    thread = threading.Thread(target=ble_listener.run_session, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Session started"})


@app.route("/session/status", methods=["GET"])
def session_status():
    return jsonify(ble_listener.get_status())


@app.route("/session/proceed", methods=["POST"])
def session_proceed():
    if ble_listener.is_running():
        return error("Session is still running")

    saved = save_readings()
    if not saved:
        return error("No readings to proceed with")

    # Clear raw so pressing Proceed twice cannot add a duplicate
    new_session()
    return jsonify({"ok": True, "message": "Reading added to the queue"})


# ---------- Dropdowns ----------

@app.route("/crops", methods=["GET"])
def crops():
    rows = run_query("SELECT DISTINCT crop FROM id_info ORDER BY crop")
    names = []
    for row in rows:
        names.append(row["crop"])
    return jsonify(names)


@app.route("/stages", methods=["GET"])
def stages():
    crop = request.args.get("crop")
    rows = run_query(
        "SELECT id, stage, variety FROM id_info WHERE crop = ? ORDER BY id", (crop,)
    )
    return jsonify(rows)


# ---------- Queue ----------

@app.route("/queue", methods=["GET"])
def queue_list():
    return jsonify(queue_manager.get_pending_list())


@app.route("/queue/<int:pending_id>", methods=["PUT"])
def queue_update(pending_id):
    changes = request.get_json() or {}
    ok, message = queue_manager.update_pending(pending_id, changes)
    if not ok:
        return error(message)
    return jsonify({"ok": True, "message": message})


@app.route("/queue/manual", methods=["POST"])
def queue_manual():
    values = request.get_json() or {}
    ok, result = queue_manager.add_manual_reading(values)
    if not ok:
        return error(result)
    return jsonify({"ok": True, "id": result})


@app.route("/queue/<int:pending_id>", methods=["DELETE"])
def queue_delete(pending_id):
    if not queue_manager.delete_pending(pending_id):
        return error("Reading not found", 404)
    return jsonify({"ok": True, "message": "Deleted"})


@app.route("/queue/<int:pending_id>/send", methods=["POST"])
def queue_send(pending_id):
    reading = queue_manager.get_pending(pending_id)
    if reading is None:
        return error("Reading not found", 404)

    if reading["crop_stage_id"] is None:
        return error("Please select the crop and stage first")

    if not send_reading(pending_id):
        return error("No threshold data found for this crop and stage")

    latest = run_query("SELECT * FROM readings_history ORDER BY id DESC LIMIT 1")
    return jsonify({"ok": True, "report": latest[0]})


# ---------- Soil Report ----------

@app.route("/report/history", methods=["GET"])
def report_history():
    rows = run_query("""
        SELECT h.*, i.crop, i.stage
        FROM readings_history h
        LEFT JOIN id_info i ON h.crop_stage_id = i.id
        ORDER BY h.id DESC
    """)
    return jsonify(rows)


@app.route("/report/latest", methods=["GET"])
def report_latest():
    rows = run_query("""
        SELECT h.*, i.crop, i.stage
        FROM readings_history h
        LEFT JOIN id_info i ON h.crop_stage_id = i.id
        ORDER BY h.id DESC LIMIT 1
    """)
    if len(rows) == 0:
        return jsonify(None)
    return jsonify(rows[0])


if __name__ == "__main__":
    database.create_id_table()
    database.create_readings_database()
    database.create_solution_database()
    database.create_readings_history()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)