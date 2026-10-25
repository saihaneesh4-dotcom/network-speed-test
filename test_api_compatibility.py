import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from api import app

client = app.test_client()


def test_legacy_mini_ookla_request():
    response = client.post("/results", json={
        "server_id": "compatibility_test_server",
        "latency_ms": 15.0,
        "jitter_ms": 1.0,
        "packet_loss_percent": 0.0,
        "download_mbps": 80.0,
        "upload_mbps": 35.0,
        "streams": 4,
        "duration_sec": 10
    })

    assert response.status_code == 200, response.get_json()
    print("PASS: Legacy Mini-Ookla request")


def test_invalid_session_id():
    response = client.post("/results", json={
        "session_id": "VAL-NONEXISTENT",
        "server_id": "compatibility_test_server",
        "latency_ms": 15.0,
        "jitter_ms": 1.0,
        "packet_loss_percent": 0.0,
        "download_mbps": 80.0,
        "upload_mbps": 35.0,
        "streams": 4,
        "duration_sec": 10
    })

    assert response.status_code == 404, response.get_json()
    print("PASS: Nonexistent session rejected")


def test_legacy_iperf3_request():
    response = client.post("/iperf3/results", json={
        "test_id": "compatibility_test_iperf3",
        "server_id": "compatibility_test_server",
        "host": "127.0.0.1",
        "port": 5201,
        "download_mbps": 75.0,
        "upload_mbps": 30.0,
        "duration_sec": 10,
        "streams": 4,
        "metrics": {},
        "raw_output": "Synthetic compatibility test"
    })

    assert response.status_code == 201, response.get_json()
    print("PASS: Legacy iperf3 request")


if __name__ == "__main__":
    test_legacy_mini_ookla_request()
    test_invalid_session_id()
    test_legacy_iperf3_request()
    print("\nAll API compatibility tests passed!")
