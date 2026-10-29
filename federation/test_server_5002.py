"""Mini-Ookla TCP measurement server for port 5002.

Wire protocol: PROBE/PROBE_ACK;
TEST UPLOAD|DOWNLOAD <session_id> <measured_duration> <ramp_up> <streams> <index>;
GO; framed W/D/END download data; RESULT <received_bytes> upload result.
"""
import math
import socket
import threading
import time
from dataclasses import dataclass, field

HOST = "0.0.0.0"
PORT = 5002
CHUNK_SIZE = 64 * 1024
MAX_STREAMS = 32
BARRIER_TIMEOUT_SEC = 15.0
START_LEAD_SEC = 1.0
SOCKET_TIMEOUT_SEC = 1.0
POST_WINDOW_DRAIN_SEC = 5.0

_sessions = {}
_sessions_lock = threading.Lock()


@dataclass
class Session:
    direction: str
    duration: float
    ramp: float
    expected: int
    connections: dict = field(default_factory=dict)
    condition: threading.Condition = field(default_factory=threading.Condition)
    go_at: float | None = None
    failed: bool = False
    finished: int = 0


def read_line(conn, limit=4096):
    buf = bytearray()
    while b"\n" not in buf:
        if len(buf) >= limit:
            raise ValueError("Protocol line too long")
        data = conn.recv(min(1024, limit - len(buf)))
        if not data:
            raise ConnectionError("Peer closed while reading line")
        buf.extend(data)
    line, _, rest = buf.partition(b"\n")
    if rest:
        raise ValueError("Unexpected data after command line")
    return line.decode("ascii").strip()


def send_frame_header(conn, kind, length):
    conn.sendall(f"{kind} {length}\n".encode("ascii"))


def register_session(direction, sid, duration, ramp, streams, index, conn):
    with _sessions_lock:
        session = _sessions.get(sid)
        if session is None:
            session = Session(direction, duration, ramp, streams)
            _sessions[sid] = session
        if (session.direction != direction or abs(session.duration - duration) > 1e-9
                or abs(session.ramp - ramp) > 1e-9 or session.expected != streams
                or index in session.connections):
            return None
        session.connections[index] = conn
    with session.condition:
        session.condition.notify_all()
    return session


def wait_for_all_streams(session):
    with session.condition:
        deadline = time.monotonic() + BARRIER_TIMEOUT_SEC
        while len(session.connections) < session.expected and not session.failed:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                session.failed = True
                session.condition.notify_all()
                break
            session.condition.wait(remaining)
        if session.failed:
            return None
        if session.go_at is None:
            session.go_at = time.monotonic() + START_LEAD_SEC
        return session.go_at


def wait_until(target):
    while True:
        remaining = target - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 0.05))


def handle_upload(conn, sid, index, go_at, duration, ramp):
    measure_start = go_at + ramp
    measure_end = measure_start + duration
    drain_deadline = measure_end + POST_WINDOW_DRAIN_SEC
    counted = 0
    while True:
        now = time.monotonic()
        if now >= drain_deadline:
            raise TimeoutError("Upload sender did not finish after measurement window")
        if now < measure_start:
            deadline = measure_start
        elif now < measure_end:
            deadline = measure_end
        else:
            deadline = drain_deadline
        conn.settimeout(max(0.01, min(SOCKET_TIMEOUT_SEC, deadline - now)))
        try:
            data = conn.recv(CHUNK_SIZE)
        except socket.timeout:
            continue
        if not data:
            break
        received_at = time.monotonic()
        if measure_start <= received_at < measure_end:
            counted += len(data)
    conn.sendall(f"RESULT {counted}\n".encode("ascii"))
    print(f"[UPLOAD {sid}:{index}] bytes={counted}, window={duration:.3f}s")


def handle_download(conn, sid, index, go_at, duration, ramp):
    measure_start = go_at + ramp
    measure_end = measure_start + duration

    # The accepted socket starts with a short command-read timeout. Download
    # sends can legitimately block under TCP flow control; avoid cutting a
    # framed payload after one second. Keep a finite timeout for dead peers.
    conn.settimeout(max(10.0, duration + ramp + 30.0))
    payload = b"x" * CHUNK_SIZE

    while time.monotonic() < measure_start:
        send_frame_header(conn, "W", len(payload))
        conn.sendall(payload)
    while time.monotonic() < measure_end:
        send_frame_header(conn, "D", len(payload))
        conn.sendall(payload)
    conn.sendall(b"END 0\n")
    print(f"[DOWNLOAD {sid}:{index}] window={duration:.3f}s complete")


def finish_session(sid, session):
    with session.condition:
        session.finished += 1
        remove = session.finished >= session.expected or session.failed
    if remove:
        with _sessions_lock:
            if _sessions.get(sid) is session:
                del _sessions[sid]


def handle_client(conn, addr):
    session = None
    sid = None
    direction = None
    index = None
    try:
        conn.settimeout(SOCKET_TIMEOUT_SEC)
        line = read_line(conn)
        parts = line.split()
        if parts == ["PROBE"]:
            conn.sendall(b"PROBE_ACK\n")
            return
        if len(parts) != 7 or parts[0] != "TEST":
            conn.sendall(b"ERROR INVALID_COMMAND\n")
            return

        _, direction, sid, duration_text, ramp_text, streams_text, index_text = parts
        if direction not in ("UPLOAD", "DOWNLOAD"):
            conn.sendall(b"ERROR INVALID_DIRECTION\n")
            return
        duration = float(duration_text)
        ramp = float(ramp_text)
        streams = int(streams_text)
        index = int(index_text)
        if (not math.isfinite(duration) or not math.isfinite(ramp)
                or not 0.1 <= duration <= 120.0 or not 0.0 <= ramp <= 30.0
                or not 1 <= streams <= MAX_STREAMS or not 0 <= index < streams):
            conn.sendall(b"ERROR INVALID_PARAMETERS\n")
            return

        session = register_session(direction, sid, duration, ramp, streams, index, conn)
        if session is None:
            conn.sendall(b"ERROR INVALID_SESSION\n")
            return
        go_at = wait_for_all_streams(session)
        if go_at is None:
            conn.sendall(b"ERROR SESSION_BARRIER_TIMEOUT\n")
            return
        wait_until(go_at)
        conn.sendall(b"GO\n")
        if direction == "UPLOAD":
            handle_upload(conn, sid, index, go_at, duration, ramp)
        else:
            handle_download(conn, sid, index, go_at, duration, ramp)
    except (OSError, ValueError, ConnectionError, TimeoutError) as exc:
        print(f"[ERROR] {direction} {sid}:{index} {addr}: {exc}")
        if session is not None:
            with session.condition:
                session.failed = True
                session.condition.notify_all()
    finally:
        if session is not None and sid is not None:
            finish_session(sid, session)
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(128)
        print(f"Mini-Ookla measurement server listening on {HOST}:{PORT}")
        print("Timing: duration is measured transfer time; ramp-up is additional and excluded.")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()