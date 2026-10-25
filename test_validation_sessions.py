import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from api import app

client = app.test_client()


def test_create_session():
    response = client.post("/validation/sessions", json={})
    assert response.status_code == 201, response.get_json()

    session = response.get_json()
    assert session["session_id"].startswith("VAL-")
    assert session["status"] == "running"
    assert session["mini_ookla_status"] == "pending"
    assert session["iperf3_status"] == "pending"

    print("PASS: Session creation")
    return session["session_id"]


def test_get_session(session_id):
    response = client.get(f"/validation/sessions/{session_id}")
    assert response.status_code == 200, response.get_json()

    session = response.get_json()
    assert session["session_id"] == session_id
    assert isinstance(session["mini_ookla_results"], list)
    assert isinstance(session["iperf3_results"], list)

    print("PASS: Session retrieval")


def test_update_session(session_id):
    response = client.patch(
        f"/validation/sessions/{session_id}",
        json={"mini_ookla_status": "running"}
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["mini_ookla_status"] == "running"

    print("PASS: Session status update")


def test_list_sessions():
    response = client.get("/validation/sessions")
    assert response.status_code == 200, response.get_json()
    assert isinstance(response.get_json(), list)

    print("PASS: Session listing")


def test_save_measurements(session_id):
    # Save a Mini-Ookla measurement.
    mini_response = client.post("/results", json={
        "session_id": session_id,
        "server_id": "validation_test_server",
        "latency_ms": 20.5,
        "jitter_ms": 1.1,
        "packet_loss_percent": 0.0,
        "download_mbps": 95.0,
        "upload_mbps": 42.0,
        "streams": 4,
        "duration_sec": 10
    })

    assert mini_response.status_code == 200, mini_response.get_json()

    # Save an iperf3 measurement under the SAME session ID.
    iperf_response = client.post("/iperf3/results", json={
        "session_id": session_id,
        "test_id": "validation_test_iperf3",
        "server_id": "validation_test_server",
        "host": "127.0.0.1",
        "port": 5201,
        "download_mbps": 92.0,
        "upload_mbps": 40.0,
        "duration_sec": 10,
        "streams": 4,
        "metrics": {},
        "raw_output": "Test fixture"
    })

    assert iperf_response.status_code == 201, iperf_response.get_json()

    # Retrieve both measurements through the session endpoint.
    response = client.get(f"/validation/sessions/{session_id}")
    assert response.status_code == 200, response.get_json()

    session = response.get_json()

    assert len(session["mini_ookla_results"]) == 1
    assert len(session["iperf3_results"]) == 1

    assert (
        session["mini_ookla_results"][0]["session_id"]
        == session_id
    )

    assert (
        session["iperf3_results"][0]["session_id"]
        == session_id
    )

    assert session["mini_ookla_status"] == "completed"
    assert session["iperf3_status"] == "completed"

    print("PASS: Mini-Ookla result saved with session ID")
    print("PASS: iperf3 result saved with the same session ID")
    print("PASS: Both measurements retrieved together")

def test_failure_reporting():
    # Create a new session.
    response = client.post("/validation/sessions", json={})
    assert response.status_code == 201, response.get_json()

    session_id = response.get_json()["session_id"]

    # Record a Mini-Ookla failure.
    response = client.patch(
        f"/validation/sessions/{session_id}",
        json={
            "mini_ookla_status": "failed",
            "mini_ookla_error": "Synthetic connection failure"
        }
    )

    assert response.status_code == 200, response.get_json()

    # Record a successful iperf3 measurement status.
    response = client.patch(
        f"/validation/sessions/{session_id}",
        json={
            "iperf3_status": "completed"
        }
    )

    assert response.status_code == 200, response.get_json()

    session = response.get_json()

    assert session["mini_ookla_status"] == "failed"
    assert session["iperf3_status"] == "completed"
    assert session["status"] == "partial"
    assert session["mini_ookla_error"] == "Synthetic connection failure"

    print("PASS: API records measurement failures")
    print("PASS: API calculates partial session status")
    print("PASS: API preserves failure details")


def test_invalid_status_rejected():
    response = client.post("/validation/sessions", json={})
    assert response.status_code == 201, response.get_json()

    session_id = response.get_json()["session_id"]

    response = client.patch(
        f"/validation/sessions/{session_id}",
        json={"mini_ookla_status": "unknown"}
    )

    assert response.status_code == 400, response.get_json()
    print("PASS: Invalid test status rejected")


if __name__ == "__main__":
    session_id = test_create_session()
    test_get_session(session_id)
    test_update_session(session_id)
    test_list_sessions()
    test_save_measurements(session_id)
    test_failure_reporting()
    test_invalid_status_rejected()

    print("\nAll validation session tests passed!")