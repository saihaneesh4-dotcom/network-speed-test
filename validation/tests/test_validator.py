from validator import validate_result


def test_valid_result():
    result = {
        "server_id": "server_01",
        "latency_ms": 25.4,
        "jitter_ms": 1.2,
        "packet_loss_percent": 0,
        "download_mbps": 95.5,
        "upload_mbps": 42.3,
        "streams": 4,
        "duration_sec": 10
    }

    valid, errors = validate_result(result)

    assert valid is True
    assert errors == []


def test_negative_latency():
    result = {
        "server_id": "server_01",
        "latency_ms": -5,
        "jitter_ms": 1.2,
        "packet_loss_percent": 0,
        "download_mbps": 95.5,
        "upload_mbps": 42.3,
        "streams": 4,
        "duration_sec": 10
    }

    valid, errors = validate_result(result)

    assert valid is False
    assert "latency_ms cannot be negative" in errors


def test_missing_duration():
    result = {
        "server_id": "server_01",
        "latency_ms": 25.4,
        "jitter_ms": 1.2,
        "packet_loss_percent": 0,
        "download_mbps": 95.5,
        "upload_mbps": 42.3,
        "streams": 4
    }

    valid, errors = validate_result(result)

    assert valid is False
    assert "Missing field: duration_sec" in errors


def test_invalid_packet_loss():
    result = {
        "server_id": "server_01",
        "latency_ms": 25.4,
        "jitter_ms": 1.2,
        "packet_loss_percent": 150,
        "download_mbps": 95.5,
        "upload_mbps": 42.3,
        "streams": 4,
        "duration_sec": 10
    }

    valid, errors = validate_result(result)

    assert valid is False
    assert "packet_loss_percent must be between 0 and 100" in errors