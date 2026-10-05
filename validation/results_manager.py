import csv
from pathlib import Path


RESULT_FIELDS = [
    "test_id",
    "tool",
    "server_id",
    "streams",
    "duration_sec",
    "latency_ms",
    "jitter_ms",
    "packet_loss_percent",
    "download_mbps",
    "upload_mbps",
    "timestamp"
]


def save_result(result, file_path):
    file_path = Path(file_path)

    file_exists = file_path.exists()

    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)


def load_results(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)