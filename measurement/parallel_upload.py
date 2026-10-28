
import socket
import threading
import time
import uuid


def upload_stream(
    host, port, duration, ramp_up_sec,
    streams, index, session_id, results
):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(duration + ramp_up_sec + 30)

    try:
        client.connect((host, port))

        command = (
            f"TEST UPLOAD {session_id} {duration} "
            f"{ramp_up_sec} {streams} {index}\n"
        )
        client.sendall(command.encode())

        response = b""
        while b"\n" not in response:
            data = client.recv(1024)
            if not data:
                raise ConnectionError("Server closed before GO")
            response += data

        line, _ = response.split(b"\n", 1)
        status = line.decode().strip()

        if status != "GO":
            raise RuntimeError(f"Server response: {status}")

        payload = b"x" * 65536
        deadline = time.monotonic() + ramp_up_sec + duration + 3

        while time.monotonic() < deadline:
            try:
                client.sendall(payload)
            except (OSError, socket.timeout):
                break

        try:
            client.shutdown(socket.SHUT_WR)
        except OSError:
            pass

        response = b""
        while b"\n" not in response:
            data = client.recv(1024)
            if not data:
                raise ConnectionError("Missing RESULT from server")
            response += data

        line = response.split(b"\n", 1)[0].decode().strip().split()

        if len(line) != 2 or line[0] != "RESULT":
            raise RuntimeError(f"Unexpected response: {' '.join(line)}")

        results[index] = int(line[1])

    except (OSError, ValueError, RuntimeError, ConnectionError) as error:
        print(f"[UPLOAD {index}] Failed: {error}")
        results[index] = 0

    finally:
        client.close()


def measure_parallel_upload(
    host, port, duration=5, streams=4, ramp_up_sec=2
):
    session_id = uuid.uuid4().hex
    results = [0] * streams
    threads = []

    for index in range(streams):
        thread = threading.Thread(
            target=upload_stream,
            args=(
                host, port, duration, ramp_up_sec,
                streams, index, session_id, results
            )
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_bytes = sum(results)
    speed = total_bytes * 8 / duration / 1_000_000

    print(f"[UPLOAD] Per-stream bytes: {results}")
    print(f"[UPLOAD] Total: {speed:.2f} Mbps")

    return speed
