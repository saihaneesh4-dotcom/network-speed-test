import socket
import time
import threading


def upload_stream(host, port, duration, ramp_up_sec):

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.connect((host, port))

    total_duration = duration + ramp_up_sec

    request = f"UPLOAD {total_duration} 1\n"
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

    data = b"x" * 65536

    measured_bytes = 0

    start_time = time.perf_counter()

    while True:

        current_time = time.perf_counter()
        elapsed = current_time - start_time

        if elapsed >= total_duration:
            break

        try:
            client.sendall(data)

        except (BrokenPipeError, ConnectionResetError):
            break

        current_time = time.perf_counter()
        elapsed = current_time - start_time

        if elapsed >= ramp_up_sec:
            measured_bytes += len(data)

    client.close()

    return measured_bytes


def measure_parallel_upload(
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

        results[index] = upload_stream(
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

    upload_mbps = (
        total_bytes * 8
    ) / duration / 1_000_000

    return upload_mbps