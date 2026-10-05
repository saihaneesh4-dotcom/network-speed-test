from flask import Flask, request, jsonify
from database import (
    save_result,
    get_results,
    get_results_by_server,
    get_latest_result
)
from datetime import datetime

app = Flask(__name__)


@app.route("/results", methods=["POST"])
def add_result():
    data = request.get_json()

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Request body must contain JSON data"
        }), 400

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
            return jsonify({
                "status": "error",
                "message": field + " is missing"
            }), 400

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
    results = get_results()

    formatted_results = []

    for result in results:
        formatted_results.append({
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
        })

    return jsonify(formatted_results)

@app.route("/results/<server_id>", methods=["GET"])
def view_server_results(server_id):
    results = get_results_by_server(server_id)

    formatted_results = []

    for result in results:
        formatted_results.append({
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
        })

    return jsonify(formatted_results)

@app.route("/results/latest", methods=["GET"])
def view_latest_result():
    result = get_latest_result()

    if result is None:
        return jsonify({
            "status": "error",
            "message": "No results available"
        }), 404

    formatted_result = {
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

    return jsonify(formatted_result)

if __name__ == "__main__":
    app.run(debug=True)