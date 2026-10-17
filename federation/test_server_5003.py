
import socket
import time
import threading

HOST = "0.0.0.0"
PORT = 5003
BUFFER_SIZE = 65536


def handle_client(conn, addr):
    print("\n[CONNECTION]", addr)

    try:
        buffer = b""

        while b"\n" not in buffer:
            data = conn.recv(1024)
            if not data:
                return
            buffer += data

        command_line, remaining = buffer.split(b"\n", 1)
        parts = command_line.decode().strip().split()

        if not parts:
            return

        command_type = parts[0]

        if command_type == "PROBE":
            conn.sendall(b"PROBE_ACK\n")
            print("[PROBE] Acknowledged")
            return

        if command_type not in ("DOWNLOAD", "UPLOAD"):
            conn.sendall(b"INVALID_COMMAND\n")
            return

        if len(parts) not in (3, 4):
            conn.sendall(b"INVALID_COMMAND\n")
            return

        try:
            duration = int(parts[1])
            streams = int(parts[2])
            ramp_up_sec = int(parts[3]) if len(parts) == 4 else 0
        except ValueError:
            conn.sendall(b"INVALID_COMMAND\n")
            return

        if duration <= 0 or streams <= 0 or ramp_up_sec < 0:
            conn.sendall(b"INVALID_COMMAND\n")
            return

        if command_type == "DOWNLOAD":
            print("[DOWNLOAD] Started:", duration, "sec")
            conn.sendall(b"READY\n")

            data = b"x" * BUFFER_SIZE
            start = time.perf_counter()
            total_bytes = 0

            try:
                while time.perf_counter() - start < duration:
                    conn.sendall(data)
                    total_bytes += len(data)
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass

            elapsed = time.perf_counter() - start

            print("[DOWNLOAD] Bytes sent:", total_bytes)
            print("[DOWNLOAD] Time:", round(elapsed, 3), "sec")

            if elapsed > 0:
                print(
                    "[DOWNLOAD] Server-side rate:",
                    round(total_bytes * 8 / elapsed / 1_000_000, 2),
                    "Mbps"
                )

        elif command_type == "UPLOAD":
            print("[UPLOAD] Started:", duration, "sec")
            print("[UPLOAD] Ramp-up:", ramp_up_sec, "sec")

            conn.sendall(b"READY\n")

            total_bytes = 0
            start = time.perf_counter()

            try:
                while True:
                    data = conn.recv(BUFFER_SIZE)

                    if not data:
                        break

                    elapsed = time.perf_counter() - start

                    if ramp_up_sec <= elapsed < duration:
                        total_bytes += len(data)

            except (ConnectionResetError, OSError):
                pass

            elapsed = time.perf_counter() - start

            print("[UPLOAD] Measured bytes received:", total_bytes)
            print("[UPLOAD] Time:", round(elapsed, 3), "sec")

            conn.sendall(f"RESULT {total_bytes}\n".encode())

    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print("[ERROR]", e)

    finally:
        conn.close()
        print("[CONNECTION] Closed")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

print("========================================")
print("   CONCURRENT MEASUREMENT SERVER")
print("========================================")
print("Host:", HOST)
print("Port:", PORT)

while True:
    conn, addr = server.accept()
    threading.Thread(
        target=handle_client,
        args=(conn, addr),
        daemon=True
    ).start()
