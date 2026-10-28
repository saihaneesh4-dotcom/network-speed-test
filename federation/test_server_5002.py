import socket
import threading
import time

HOST = "0.0.0.0"
PORT = 5002
BUFFER_SIZE = 65536
BARRIER_TIMEOUT = 15

sessions = {}
sessions_lock = threading.Lock()


def read_line(conn, initial=b""):
    buffer = initial
    while b"\n" not in buffer:
        data = conn.recv(4096)
        if not data:
            raise ConnectionError("Connection closed")
        buffer += data
    line, remaining = buffer.split(b"\n", 1)
    return line.decode().strip(), remaining


def send_frame(conn, kind, payload):
    conn.sendall(f"{kind} {len(payload)}\n".encode() + payload)


def handle_client(conn, addr):
    session = None
    session_id = None

    try:
        conn.settimeout(30)
        line, pending = read_line(conn)
        parts = line.split()

        if parts == ["PROBE"]:
            conn.sendall(b"PROBE_ACK\n")
            return

        # TEST direction session_id duration ramp_up streams index
        if len(parts) != 7 or parts[0] != "TEST":
            conn.sendall(b"INVALID_COMMAND\n")
            return

        _, direction, session_id, duration_s, ramp_s, streams_s, index_s = parts

        duration = float(duration_s)
        ramp = float(ramp_s)
        streams = int(streams_s)
        index = int(index_s)

        if (
            direction not in ("UPLOAD", "DOWNLOAD")
            or duration <= 0
            or ramp < 0
            or streams < 1
            or not 0 <= index < streams
        ):
            conn.sendall(b"INVALID_COMMAND\n")
            return

        with sessions_lock:
            session = sessions.get(session_id)

            if session is None:
                session = {
                    "direction": direction,
                    "duration": duration,
                    "ramp": ramp,
                    "expected": streams,
                    "connections": {},
                    "condition": threading.Condition(),
                    "start": None,
                    "failed": False,
                    "finished": 0,
                }
                sessions[session_id] = session

            if (
                session["direction"] != direction
                or session["duration"] != duration
                or session["ramp"] != ramp
                or session["expected"] != streams
                or index in session["connections"]
            ):
                conn.sendall(b"INVALID_SESSION\n")
                return

            session["connections"][index] = conn

        condition = session["condition"]

        with condition:
            condition.notify_all()
            deadline = time.monotonic() + BARRIER_TIMEOUT

            while len(session["connections"]) < streams:
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    session["failed"] = True
                    condition.notify_all()
                    break

                condition.wait(remaining)

            if session["failed"]:
                conn.sendall(b"SESSION_FAILED\n")
                return

            if session["start"] is None:
                # Shared server clock, with a short lead-in.
                session["start"] = time.perf_counter() + 1.0

            start = session["start"]

        conn.sendall(b"GO\n")

        measure_start = start + ramp
        measure_end = measure_start + duration
        payload = b"x" * BUFFER_SIZE

        if direction == "UPLOAD":
            received_bytes = 0

            while time.perf_counter() < measure_end:
                now = time.perf_counter()

                if now < measure_start:
                    timeout = measure_start - now
                else:
                    timeout = measure_end - now

                conn.settimeout(max(0.001, min(timeout, 1.0)))

                try:
                    data = conn.recv(BUFFER_SIZE)
                except socket.timeout:
                    continue

                if not data:
                    break

                received_at = time.perf_counter()

                if measure_start <= received_at < measure_end:
                    received_bytes += len(data)

            conn.sendall(f"RESULT {received_bytes}\n".encode())
            print(f"[UPLOAD {session_id}:{index}] {received_bytes} bytes")

        else:
            # W = warm-up; D = measured download data.
            while time.perf_counter() < measure_start:
                send_frame(conn, "W", payload)

            while time.perf_counter() < measure_end:
                send_frame(conn, "D", payload)

            conn.sendall(b"END 0\n")
            print(f"[DOWNLOAD {session_id}:{index}] Finished")

    except (OSError, ValueError, ConnectionError) as error:
        print(f"[ERROR] {addr}: {error}")

    finally:
        if session is not None:
            condition = session["condition"]

            with condition:
                session["finished"] += 1

                if session["finished"] >= session["expected"]:
                    with sessions_lock:
                        if sessions.get(session_id) is session:
                            del sessions[session_id]

        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        print(f"Mini-Ookla server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            ).start()


if __name__ == "__main__":
    main()