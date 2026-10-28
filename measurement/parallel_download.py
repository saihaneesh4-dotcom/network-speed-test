
import socket
import threading
import uuid


def read_line(conn, initial=b""):
    buffer = initial

    while b"\n" not in buffer:
        data = conn.recv(4096)
        if not data:
            raise ConnectionError("Connection closed")
        buffer += data

    line, remaining = buffer.split(b"\n", 1)
    return line.decode().strip(), remaining


def recv_exact(conn, size, initial=b""):
    buffer = initial

    while len(buffer) < size:
        data = conn.recv(min(65536, size - len(buffer)))
        if not data:
            raise ConnectionError("Connection closed during frame")
        buffer += data

    return buffer[:size], buffer[size:]


def download_stream(
    host, port, duration, ramp_up_sec,
    streams, index, session_id, results
):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(duration + ramp_up_sec + 30)
    measured_bytes = 0

    try:
        client.connect((host, port))

        command = (
            f"TEST DOWNLOAD {session_id} {duration} "
            f"{ramp_up_sec} {streams} {index}\n"
        )
        client.sendall(command.encode())

        line, pending = read_line(client)

        if line != "GO":
            raise RuntimeError(f"Server response: {line}")

        while True:
            line, pending = read_line(client, pending)
            parts = line.split()

            if len(parts) != 2:
                raise RuntimeError(f"Invalid frame header: {line}")

            kind, length_text = parts
            length = int(length_text)

            if kind == "END":
                break

            if kind not in ("W", "D") or length < 0:
                raise RuntimeError(f"Invalid frame: {line}")

            data, pending = recv_exact(client, length, pending)

            if kind == "D":
                measured_bytes += len(data)

        results[index] = measured_bytes

    except (OSError, ValueError, RuntimeError, ConnectionError) as error:
        print(f"[DOWNLOAD {index}] Failed: {error}")
        results[index] = 0

    finally:
        client.close()


def measure_parallel_download(
    host, port, duration=5, streams=4, ramp_up_sec=2
):
    session_id = uuid.uuid4().hex
    results = [0] * streams
    threads = []

    for index in range(streams):
        thread = threading.Thread(
            target=download_stream,
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

    print(f"[DOWNLOAD] Per-stream bytes: {results}")
    print(f"[DOWNLOAD] Total: {speed:.2f} Mbps")

    return speed
