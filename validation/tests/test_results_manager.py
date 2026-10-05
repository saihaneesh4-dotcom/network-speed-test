from results_manager import save_result, load_results


def test_save_and_load_result(tmp_path):
    file_path = tmp_path / "test_results.csv"

    result = {
        "test_id": "001",
        "tool": "Mini-Ookla",
        "server_id": "server_02",
        "streams": 4,
        "duration_sec": 10,
        "latency_ms": 21.4,
        "jitter_ms": 1.2,
        "packet_loss_percent": 0.0,
        "download_mbps": 95.5,
        "upload_mbps": 42.3,
        "timestamp": "2026-09-12 15:00:00"
    }

    save_result(result, file_path)

    results = load_results(file_path)

    assert len(results) == 1
    assert results[0]["test_id"] == "001"
    assert results[0]["tool"] == "Mini-Ookla"
    assert results[0]["server_id"] == "server_02"
    assert results[0]["streams"] == "4"
    assert results[0]["download_mbps"] == "95.5"