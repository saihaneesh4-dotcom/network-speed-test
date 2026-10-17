
import os
from datetime import datetime

from flask import Flask, request, jsonify

from database import (
    save_result,
    get_results,
    get_results_by_server,
    get_latest_result,
    register_server,
    record_heartbeat,
    get_registered_servers,
    deregister_server
)

app = Flask(__name__)

HEARTBEAT_TIMEOUT_SECONDS = int(
    os.environ.get("SERVER_HEARTBEAT_TIMEOUT_SECONDS", "30")
)

if HEARTBEAT_TIMEOUT_SECONDS < 1:
    raise ValueError("SERVER_HEARTBEAT_TIMEOUT_SECONDS must be at least 1")


def error_response(message, status_code):
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def get_json_body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None

    return data


def valid_text(value):
    return isinstance(value, str) and bool(value.strip())


def format_result(result):
    return {
        "id": result[0],
        "server_id": result[1],
        "latency_ms": result[2],
        "jitter_ms": result[3],
        "packet_loss_percent": result[4],
        "download_mbps": result[5],
        "upload_mbps": result[6],
        "streams": result[7],
        "duration_sec": result[8],
        "timestamp": result[9]
    }


# Existing results endpoints

@app.route("/results", methods=["POST"])
def add_result():
    data = get_json_body()

    if data is None:
        return error_response(
            "Request body must contain a JSON object", 400
        )

    required_fields = [
        "server_id",
        "latency_ms",
        "jitter_ms",
        "packet_loss_percent",
        "download_mbps",
        "upload_mbps",
        "streams",
        "duration_sec"
    ]

    for field in required_fields:
        if field not in data:
            return error_response(field + " is missing", 400)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_result(
        data["server_id"],
        data["latency_ms"],
        data["jitter_ms"],
        data["packet_loss_percent"],
        data["download_mbps"],
        data["upload_mbps"],
        data["streams"],
        data["duration_sec"],
        timestamp
    )

    return jsonify({
        "status": "success",
        "message": "Result saved"
    }), 200


@app.route("/results", methods=["GET"])
def view_results():
    return jsonify([format_result(r) for r in get_results()])


@app.route("/results/<server_id>", methods=["GET"])
def view_server_results(server_id):
    return jsonify([
        format_result(r) for r in get_results_by_server(server_id)
    ])


@app.route("/results/latest", methods=["GET"])
def view_latest_result():
    result = get_latest_result()

    if result is None:
        return error_response("No results available", 404)

    return jsonify(format_result(result))


# New server registry endpoints

@app.route("/servers/register", methods=["POST"])
def register_server_endpoint():
    data = get_json_body()

    if data is None:
        return error_response(
            "Request body must contain a JSON object", 400
        )

    required_fields = ["server_id", "host", "port", "location"]

    for field in required_fields:
        if field not in data:
            return error_response(field + " is missing", 400)

    server_id = data["server_id"]
    host = data["host"]
    port = data["port"]
    location = data["location"]

    if not valid_text(server_id):
        return error_response("server_id must be a non-empty string", 400)

    if not valid_text(host):
        return error_response("host must be a non-empty string", 400)

    if not valid_text(location):
        return error_response("location must be a non-empty string", 400)

    if (
        isinstance(port, bool)
        or not isinstance(port, int)
        or not 1 <= port <= 65535
    ):
        return error_response(
            "port must be an integer between 1 and 65535", 400
        )

    is_new = register_server(
        server_id.strip(),
        host.strip(),
        port,
        location.strip()
    )

    servers = get_registered_servers(HEARTBEAT_TIMEOUT_SECONDS)
    server = next(
        item for item in servers
        if item["server_id"] == server_id.strip()
    )

    return jsonify({
        "status": "success",
        "message": (
            "Server registered successfully"
            if is_new else "Server registration updated successfully"
        ),
        "server": server
    }), 201 if is_new else 200


@app.route("/servers/heartbeat", methods=["POST"])
def heartbeat_endpoint():
    data = get_json_body()

    if data is None:
        return error_response(
            "Request body must contain a JSON object", 400
        )

    server_id = data.get("server_id")

    if not valid_text(server_id):
        return error_response("server_id must be a non-empty string", 400)

    server_id = server_id.strip()

    if not record_heartbeat(server_id):
        return error_response("Server is not registered", 404)

    return jsonify({
        "status": "success",
        "message": "Heartbeat recorded",
        "server_id": server_id
    }), 200


@app.route("/servers", methods=["GET"])
def list_servers_endpoint():
    servers = get_registered_servers(HEARTBEAT_TIMEOUT_SECONDS)

    return jsonify({
        "servers": servers,
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS
    }), 200


@app.route("/servers/<server_id>", methods=["DELETE"])
def deregister_server_endpoint(server_id):
    if not server_id.strip():
        return error_response("server_id must not be empty", 400)

    if not deregister_server(server_id):
        return error_response("Server is not registered", 404)

    return jsonify({
        "status": "success",
        "message": "Server deregistered successfully",
        "server_id": server_id
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
