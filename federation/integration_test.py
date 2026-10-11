import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
import requests
from measurement.measurement_engine import run_test
from server_selector import select_best_server

server = select_best_server()

if server is None:
    print("No server available")
    exit()

print()
print("Selected server:", server["server_id"])

measurement = run_test(
    host=server["host"],
    port=server["port"],
    duration_sec=5,
    streams=4,
    ramp_up_sec=2
)

if measurement is None:
    print("Measurement failed")
    exit()

result = {
    "server_id": server["server_id"],
    "latency_ms": measurement["latency_ms"],
    "jitter_ms": measurement["jitter_ms"],
    "packet_loss_percent": measurement["packet_loss_percent"],
    "download_mbps": measurement["download_mbps"],
    "upload_mbps": measurement["upload_mbps"],
    "streams": measurement["streams"],
    "duration_sec": measurement["duration_sec"]
}

try:
    response = requests.post(
        "http://127.0.0.1:5000/results",
        json=result,
        timeout=5
    )

    if response.status_code == 200:
        print("Backend response:")
        print(response.json())
    else:
        print("Backend returned error:", response.status_code)

except requests.exceptions.ConnectionError:
    print("Could not connect to backend API.")

except requests.exceptions.Timeout:
    print("Backend request timed out.")