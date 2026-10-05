import socket
import time

from measurement.parallel_download import measure_parallel_download
from measurement.parallel_upload import measure_parallel_upload


def measure_latency(host, port, num_probes=20):

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((host, port))
        client.settimeout(1)

        latencies = []
        lost_probes = 0

        for _ in range(num_probes):

            try:

                start = time.perf_counter()

                client.sendall(b"PROBE\n")

                buffer = b""

                while b"\n" not in buffer:

                    data = client.recv(1024)

                    if data == b"":
                        break

                    buffer += data

                if b"\n" not in buffer:
                    lost_probes += 1
                    continue

                response = buffer.split(b"\n", 1)[0]
                response = response.decode().strip()

                if response != "PROBE_ACK":
                    lost_probes += 1
                    continue

                end = time.perf_counter()

                latency = (end - start) * 1000

                latencies.append(latency)

            except socket.timeout:

                lost_probes += 1

        if len(latencies) == 0:
            return None

        average_latency = (
            sum(latencies) / len(latencies)
        )

        if len(latencies) > 1:

            jitter = sum(
                abs(latencies[i] - latencies[i - 1])
                for i in range(1, len(latencies))
            ) / (len(latencies) - 1)

        else:

            jitter = 0

        packet_loss = (
            lost_probes / num_probes
        ) * 100

        return {
            "latency_ms": average_latency,
            "jitter_ms": jitter,
            "packet_loss_percent": packet_loss
        }

    finally:

        client.close()


def run_test(
    host,
    port,
    duration_sec=5,
    streams=4,
    ramp_up_sec=2
):

    print()
    print("========================================")
    print("          MEASUREMENT ENGINE")
    print("========================================")

    print("Host  :", host)
    print("Port  :", port)

    # ---------------- LATENCY ----------------

    print()
    print("[1/3] Measuring latency...")

    latency_result = measure_latency(
        host,
        port
    )

    if latency_result is None:

        print("Latency test failed")

        return None

    print(
        "Latency:",
        round(latency_result["latency_ms"], 2),
        "ms"
    )

    print(
        "Jitter:",
        round(latency_result["jitter_ms"], 2),
        "ms"
    )

    print(
        "Packet loss:",
        round(
            latency_result["packet_loss_percent"],
            2
        ),
        "%"
    )

    # ---------------- DOWNLOAD ----------------

    print()
    print("[2/3] Measuring download...")

    download_mbps = measure_parallel_download(
        host,
        port,
        duration=duration_sec,
        streams=streams,
        ramp_up_sec=ramp_up_sec
    )

    print(
        "Download:",
        round(download_mbps, 2),
        "Mbps"
    )

    # ---------------- UPLOAD ----------------

    print()
    print("[3/3] Measuring upload...")

    upload_mbps = measure_parallel_upload(
        host,
        port,
        duration=duration_sec,
        streams=streams,
        ramp_up_sec=ramp_up_sec
    )

    print(
        "Upload:",
        round(upload_mbps, 2),
        "Mbps"
    )

    # ---------------- FINAL RESULT ----------------

    result = {

        "latency_ms":
            latency_result["latency_ms"],

        "jitter_ms":
            latency_result["jitter_ms"],

        "packet_loss_percent":
            latency_result["packet_loss_percent"],

        "download_mbps":
            download_mbps,

        "upload_mbps":
            upload_mbps,

        "streams":
            streams,

        "duration_sec":
            duration_sec
    }

    print()
    print("========================================")
    print("            FINAL RESULT")
    print("========================================")

    print(
        "Latency      :",
        round(result["latency_ms"], 2),
        "ms"
    )
    print(
        "Jitter       :",
        round(result["jitter_ms"], 2),
        "ms"
    )
    print(
        "Packet loss  :",
        round(result["packet_loss_percent"], 2),
        "%"
    )
    print(
        "Download     :",
        round(result["download_mbps"], 2),
        "Mbps"
    )
    print(
        "Upload       :",
        round(result["upload_mbps"], 2),
        "Mbps"
    )
    print("Streams      :", result["streams"])
    print("Duration     :", result["duration_sec"], "sec")

    print("========================================")

    return result