
import hmac
import json
import os
import tempfile
import math
import ipaddress
from pathlib import Path
from threading import Lock
from datetime import datetime


from flask import Flask, jsonify, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "validation_results" / "iperf3_results.json"

# Configure these in PowerShell before starting the receiver.
UPLOAD_TOKEN = os.environ.get("IPERF3_UPLOAD_TOKEN", "")
PORT = int(os.environ.get("IPERF3_RECEIVER_PORT", "8765"))

file_lock = Lock()


def error(message, status):
    return jsonify({"status": "error", "message": message}), status


def valid_trial(trial):
    if not isinstance(trial, dict):
        return False, "Trial must be a JSON object"

    required = {
        "client_id", "trial_id", "timestamp", "server_ip", "server_port",
        "protocol", "streams", "duration_sec", "omit_sec",
        "upload_mbps", "download_mbps",
    }

    missing = required - trial.keys()
    if missing:
        return False, f"Missing fields: {', '.join(sorted(missing))}"

    integer_fields = (
        "trial_id", "server_port", "streams", "duration_sec", "omit_sec"
    )

    for field in integer_fields:
        value = trial[field]
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"{field} must be an integer"

    if trial["trial_id"] < 1:
        return False, "trial_id must be positive"

    if not 1 <= trial["server_port"] <= 65535:
        return False, "server_port is out of range"

    if trial["streams"] < 1 or trial["duration_sec"] < 1:
        return False, "streams and duration_sec must be positive"

    if not 0 <= trial["omit_sec"] < trial["duration_sec"]:
        return False, "omit_sec must be non-negative and less than duration_sec"

    if trial["protocol"] != "TCP":
        return False, "Only TCP trials are currently supported"

    timestamp = trial["timestamp"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        return False, "timestamp must be a non-empty string"

    try:
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed_timestamp.tzinfo is None:
            return False, "timestamp must include a timezone"
    except ValueError:
        return False, "timestamp must be a valid ISO 8601 timestamp"

    server_ip = trial["server_ip"]
    if not isinstance(server_ip, str) or not server_ip.strip():
        return False, "server_ip must be a non-empty string"

    try:
        ipaddress.ip_address(server_ip)
    except ValueError:
        return False, "server_ip must be a valid IP address"

    for field in ("upload_mbps", "download_mbps"):
        speed = trial[field]
        if (
            isinstance(speed, bool)
            or not isinstance(speed, (int, float))
            or not math.isfinite(speed)
            or speed < 0
        ):
            return False, f"{field} must be a finite, non-negative number"
        client_id = trial["client_id"]
    if (
        not isinstance(client_id, str)
        or not client_id.strip()
        or len(client_id) > 100
    ):
        return False, "client_id must be a non-empty string of at most 100 characters"

    return True, ""



def load_results():
    if not RESULTS_FILE.exists():
        return {
            "schema_version": 1,
            "test_type": "iperf3",
            "results": [],
        }

    with RESULTS_FILE.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("test_type") != "iperf3"
        or not isinstance(data.get("results"), list)
    ):
        raise ValueError("Existing results file has an unexpected schema")

    return data


def atomic_save(data):
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix="iperf3_", suffix=".tmp", dir=RESULTS_FILE.parent
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_name, RESULTS_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


@app.get("/health")
def health():
    return jsonify({"status": "success", "service": "iperf3-receiver"})


@app.get("/api/iperf3/results")
def get_iperf3_results():
    try:
        with file_lock:
            data = load_results()
        return jsonify(data), 200
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        app.logger.exception("Unable to read iperf3 results")
        return error(str(exc), 500)



@app.post("/api/iperf3/results")
def receive_iperf3_result():
    if not UPLOAD_TOKEN:
        return error("Receiver upload token is not configured", 503)

    supplied_token = request.headers.get("X-Upload-Token", "")
    if not hmac.compare_digest(supplied_token, UPLOAD_TOKEN):
        return error("Invalid or missing upload token", 401)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be a JSON object", 400)

    trial = data.get("result")
    if not isinstance(trial, dict):
        return error("Expected a single trial in the 'result' field", 400)

    ok, message = valid_trial(trial)
    if not ok:
        return error(message, 400)

    try:
        with file_lock:
            stored = load_results()
            existing = stored["results"]

            # Each client has its own sequential trial IDs.
            same_trial = [
                item for item in existing
                if item.get("client_id") == trial["client_id"]
                and item.get("trial_id") == trial["trial_id"]
            ]

            if any(item == trial for item in same_trial):
                return jsonify({
                    "status": "success",
                    "message": "This trial was already stored",
                    "duplicate": True,
                    "client_id": trial["client_id"],
                    "trial_id": trial["trial_id"],
                }), 200

            if same_trial:
                return error(
                    "This client_id and trial_id already exist with different content",
                    409,
                )

            stored["results"].append(trial)
            atomic_save(stored)

        return jsonify({
            "status": "success",
            "message": "Trial stored successfully",
            "duplicate": False,
            "client_id": trial["client_id"],
            "trial_id": trial["trial_id"],
        }), 201

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        app.logger.exception("Unable to store iperf3 trial")
        return error(str(exc), 500)



if __name__ == "__main__":
    if not UPLOAD_TOKEN:
        raise SystemExit(
            "Set IPERF3_UPLOAD_TOKEN before starting the receiver."
        )

    cert_file = BASE_DIR / "certs" / "iperf3-receiver.pem"
    key_file = BASE_DIR / "certs" / "iperf3-receiver-key.pem"

    if not cert_file.is_file() or not key_file.is_file():
        raise SystemExit("HTTPS certificate or private key is missing.")

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        ssl_context=(str(cert_file), str(key_file)),
    )