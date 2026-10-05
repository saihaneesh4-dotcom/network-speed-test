import requests
from server_selector import select_best_server

server = select_best_server()

if server is None:
    print("No server available")
    exit()

print()
print("Selected server:", server["server_id"])

result = {
    "server_id": server["server_id"],
    "latency_ms": server["latency_ms"],
    "jitter_ms": 1.0,
    "packet_loss_percent": 0.0,
    "download_mbps": 100.0,
    "upload_mbps": 45.0,
    "streams": 4,
    "duration_sec": 10
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