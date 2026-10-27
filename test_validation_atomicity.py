import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import database
from api import app


@pytest.fixture
def client_and_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test_results.db"))
    database.create_table()
    app.config.update(TESTING=False)
    with app.test_client() as client:
        yield client


def create_session(client):
    response = client.post("/validation/sessions", json={})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["session_id"]


def mini_payload(session_id):
    return {
        "session_id": session_id,
        "server_id": "atomicity-test-server",
        "latency_ms": 20.5,
        "jitter_ms": 1.1,
        "packet_loss_percent": 0.0,
        "download_mbps": 95.0,
        "upload_mbps": 42.0,
        "streams": 4,
        "duration_sec": 10,
    }


def iperf_payload(session_id):
    return {
        "session_id": session_id,
        "test_id": "atomicity-test",
        "download_mbps": 92.0,
        "upload_mbps": 40.0,
        "duration_sec": 10,
        "streams": 4,
        "metrics": {},
        "raw_output": "Test fixture",
    }


def test_session_result_and_status_are_saved_together(client_and_db):
    client = client_and_db
    session_id = create_session(client)

    response = client.post("/results", json=mini_payload(session_id))
    assert response.status_code == 200, response.get_json()

    session = client.get(f"/validation/sessions/{session_id}").get_json()
    assert len(session["mini_ookla_results"]) == 1
    assert session["mini_ookla_status"] == "completed"


def test_late_result_rejected_after_test_failed(client_and_db):
    client = client_and_db
    session_id = create_session(client)
    response = client.patch(
        f"/validation/sessions/{session_id}",
        json={"iperf3_status": "failed", "iperf3_error": "synthetic failure"},
    )
    assert response.status_code == 200

    before = len(database.get_iperf3_results())
    response = client.post("/iperf3/results", json=iperf_payload(session_id))

    assert response.status_code == 409, response.get_json()
    assert len(database.get_iperf3_results()) == before


def test_result_insert_rolls_back_if_session_update_fails(client_and_db):
    client = client_and_db
    session_id = create_session(client)

    connection = database.get_connection()
    connection.execute(f"""
        CREATE TRIGGER force_session_update_failure
        BEFORE UPDATE ON validation_sessions
        WHEN NEW.session_id = '{session_id}'
        BEGIN
            SELECT RAISE(ABORT, 'forced update failure');
        END
    """)
    connection.commit()
    connection.close()

    before = len(database.get_results())
    response = client.post("/results", json=mini_payload(session_id))

    assert response.status_code == 500
    assert len(database.get_results()) == before

    connection = database.get_connection()
    connection.execute("DROP TRIGGER force_session_update_failure")
    connection.commit()
    connection.close()


def test_legacy_result_without_session_id_still_works(client_and_db):
    client = client_and_db
    response = client.post("/iperf3/results", json={
        "download_mbps": 10,
        "upload_mbps": 5,
    })
    assert response.status_code == 201, response.get_json()
