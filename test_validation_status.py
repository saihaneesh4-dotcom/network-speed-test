import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from database import create_validation_session, update_validation_session


def test_completed_session():
    session = create_validation_session()
    session_id = session["session_id"]

    update_validation_session(
        session_id,
        mini_ookla_status="completed"
    )

    session = update_validation_session(
        session_id,
        iperf3_status="completed"
    )

    assert session["status"] == "completed"
    print("PASS: Both tests completed")


def test_partial_session():
    session = create_validation_session()
    session_id = session["session_id"]

    update_validation_session(
        session_id,
        mini_ookla_status="completed"
    )

    session = update_validation_session(
        session_id,
        iperf3_status="failed",
        iperf3_error="Synthetic test failure"
    )

    assert session["status"] == "partial"
    assert session["iperf3_error"] == "Synthetic test failure"
    print("PASS: One test succeeded and the other failed")


def test_failed_session():
    session = create_validation_session()
    session_id = session["session_id"]

    update_validation_session(
        session_id,
        mini_ookla_status="failed",
        mini_ookla_error="Synthetic Mini-Ookla failure"
    )

    session = update_validation_session(
        session_id,
        iperf3_status="failed",
        iperf3_error="Synthetic iperf3 failure"
    )

    assert session["status"] == "failed"
    print("PASS: Both tests failed")


def test_running_session():
    session = create_validation_session()
    session_id = session["session_id"]

    session = update_validation_session(
        session_id,
        mini_ookla_status="running"
    )

    assert session["status"] == "running"
    print("PASS: Session remains running")


if __name__ == "__main__":
    test_completed_session()
    test_partial_session()
    test_failed_session()
    test_running_session()

    print("\nAll validation status tests passed!")