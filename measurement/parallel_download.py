
import socket
import time
import threading


def download_stream(host, port, duration, ramp_up_sec, start_event):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(duration + ramp_up_sec + 5)

    measured_bytes = 0

    try:
        client.connect((host, port))
        total_duration = duration + ramp_up_sec
        client.sendall(f"DOWNLOAD {total_duration} 1\n".encode())

        buffer = b""

        while b"\n" not in buffer:
            data = client.recv(1024)
            if not data:
                return 0
            buffer += data

        response, remaining_data = buffer.split(b"\n", 1)

        if response.decode().strip() != "READY":
            return 0

        start_event.wait()
        start_time = time.perf_counter()
        end_time = start_time + duration

        while time.perf_counter() < end_time:
            data = client.recv(65536)

            if not data:
                break

            measured_bytes += len(data)

        return measured_bytes

    except (OSError, socket.timeout):
        return 0

    finally:
        client.close()


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
        results[index] = download_stream(
            host, port, duration, ramp_up_sec, start_event
        )

    for i in range(streams):
        thread = threading.Thread(target=run_stream, args=(i,))
        threads.append(thread)
        thread.start()

    start_event.set()

    for thread in threads:
        thread.join()

    total_bytes = sum(results)
    return total_bytes * 8 / duration / 1_000_000
