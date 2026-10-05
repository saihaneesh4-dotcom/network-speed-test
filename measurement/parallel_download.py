import socket
import time
import threading


def download_stream(host, port, duration, ramp_up_sec):

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.connect((host, port))

    total_duration = duration + ramp_up_sec

    request = f"DOWNLOAD {total_duration} 1\n"
    client.sendall(request.encode())

    buffer = b""

    while b"\n" not in buffer:

        data = client.recv(1024)

        if data == b"":
            client.close()
            return 0

        buffer += data

    response, remaining_data = buffer.split(b"\n", 1)

    response = response.decode().strip()

    if response != "READY":
        client.close()
        return 0

    measured_bytes = 0

    start_time = time.perf_counter()

    while True:

        data = client.recv(65536)

        if data == b"":
            break

        current_time = time.perf_counter()
        elapsed = current_time - start_time

        if elapsed >= ramp_up_sec:
            measured_bytes += len(data)

    client.close()

    return measured_bytes


def measure_parallel_download(
    host,
    port,
    duration=5,
    streams=4,
    ramp_up_sec=2
):

    results = [0] * streams
    threads = []

    start_event = threading.Event()

    def run_stream(index):

        start_event.wait()

        results[index] = download_stream(
            host,
            port,
            duration,
            ramp_up_sec
        )

    for i in range(streams):

        thread = threading.Thread(
            target=run_stream,
            args=(i,)
        )

        threads.append(thread)
        thread.start()

    start_event.set()

    for thread in threads:
        thread.join()

    total_bytes = sum(results)

    download_mbps = (
        total_bytes * 8
    ) / duration / 1_000_000

    return download_mbps