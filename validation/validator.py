REQUIRED_FIELDS = [
    "server_id",
    "latency_ms",
    "jitter_ms",
    "packet_loss_percent",
    "download_mbps",
    "upload_mbps",
    "streams",
    "duration_sec"
]


def validate_result(result):
    errors = []

    # Check whether all required fields are present
    for field in REQUIRED_FIELDS:
        if field not in result:
            errors.append(f"Missing field: {field}")

    # Stop here if required fields are missing
    if errors:
        return False, errors

    # Validate server ID
    if not isinstance(result["server_id"], str) or not result["server_id"].strip():
        errors.append("server_id must be a non-empty string")

    # Validate latency
    if result["latency_ms"] < 0:
        errors.append("latency_ms cannot be negative")

    # Validate jitter
    if result["jitter_ms"] < 0:
        errors.append("jitter_ms cannot be negative")

    # Validate packet loss
    if result["packet_loss_percent"] < 0 or result["packet_loss_percent"] > 100:
        errors.append("packet_loss_percent must be between 0 and 100")

    # Validate download speed
    if result["download_mbps"] < 0:
        errors.append("download_mbps cannot be negative")

    # Validate upload speed
    if result["upload_mbps"] < 0:
        errors.append("upload_mbps cannot be negative")

    # Validate number of streams
    if result["streams"] <= 0:
        errors.append("streams must be greater than 0")

    # Validate duration
    if result["duration_sec"] <= 0:
        errors.append("duration_sec must be greater than 0")

    if errors:
        return False, errors

    return True, []