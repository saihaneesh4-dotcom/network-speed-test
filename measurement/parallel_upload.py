
import socket
import time
import threading


def upload_stream(host, port, duration, ramp_up_sec):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(2)

    try:
        client.connect((host, port))
        total_duration = duration + ramp_up_sec

        client.sendall(
            f"UPLOAD {total_duration} 1 {ramp_up_sec}\n".encode()
        )

        buffer = b""

        while b"\n" not in buffer:
            data = client.recv(1024)
            if not data:
                return 0
            buffer += data

        response, remaining = buffer.split(b"\n", 1)

        if response.decode().strip() != "READY":
            return 0

        start_time = time.perf_counter()
        data = b"x" * 65536

        while time.perf_counter() - start_time < total_duration:
            try:
                client.sendall(data)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                break

        try:
            client.shutdown(socket.SHUT_WR)
        except OSError:
            return 0

        client.settimeout(5)
        buffer = remaining

        while b"\n" not in buffer:
            received = client.recv(1024)
            if not received:
                return 0
            buffer += received

        response = buffer.split(b"\n", 1)[0].decode().strip()
        parts = response.split()

        if len(parts) == 2 and parts[0] == "RESULT":
            return int(parts[1])

        return 0

    except (OSError, ValueError):
        return 0

    finally:
        client.close()


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
            host, port, duration, ramp_up_sec
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
