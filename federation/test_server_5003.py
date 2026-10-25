import socket
import time
import threading


HOST = "0.0.0.0"
PORT = 5003
BUFFER_SIZE = 65536


def handle_client(conn, addr):

    print()
    print("[CONNECTION]", addr)

    try:

        while True:

            command = conn.recv(1024).decode().strip()

            if not command:
                break

            parts = command.split()

            # ---------------- PROBE ----------------

            if command == "PROBE":

                conn.sendall(b"PROBE_ACK\n")

                print("[PROBE] Acknowledged")

                continue

            # ---------------- VALIDATE ----------------

            if len(parts) != 3:

                conn.sendall(b"INVALID_COMMAND\n")

                continue

            command_type = parts[0]

            try:

                duration = int(parts[1])
                streams = int(parts[2])

            except ValueError:

                conn.sendall(b"INVALID_COMMAND\n")

                continue

            if duration <= 0 or streams <= 0:

                conn.sendall(b"INVALID_COMMAND\n")

                continue

            # ---------------- DOWNLOAD ----------------

            if command_type == "DOWNLOAD":

                print("[DOWNLOAD] Started")
                print("  Duration :", duration, "sec")
                print("  Stream   :", streams)

                conn.sendall(b"READY\n")

                data = b"x" * BUFFER_SIZE

                total_bytes = 0

                start = time.perf_counter()

                try:

                    while time.perf_counter() - start < duration:

                        conn.sendall(data)

                        total_bytes += len(data)

                except (ConnectionResetError, BrokenPipeError):

                    print("[DOWNLOAD] Client disconnected")

                elapsed = time.perf_counter() - start

                print()
                print("[DOWNLOAD] Completed")
                print("  Bytes      :", total_bytes)
                print("  Time       :", round(elapsed, 3), "sec")

                if elapsed > 0:

                    speed = (
                        total_bytes * 8
                    ) / elapsed / 1_000_000

                    print(
                        "  Throughput :",
                        round(speed, 2),
                        "Mbps"
                    )

                break

            # ---------------- UPLOAD ----------------

            elif command_type == "UPLOAD":

                print("[UPLOAD] Started")
                print("  Duration :", duration, "sec")
                print("  Stream   :", streams)

                conn.sendall(b"READY\n")

                total_bytes = 0

                start = time.perf_counter()

                try:

                    while time.perf_counter() - start < duration:

                        data = conn.recv(BUFFER_SIZE)

                        if not data:
                            break

                        total_bytes += len(data)

                except ConnectionResetError:

                    print("[UPLOAD] Client disconnected")

                elapsed = time.perf_counter() - start

                print()
                print("[UPLOAD] Completed")
                print("  Bytes      :", total_bytes)
                print("  Time       :", round(elapsed, 3), "sec")

                if elapsed > 0:

                    speed = (
                        total_bytes * 8
                    ) / elapsed / 1_000_000

                    print(
                        "  Throughput :",
                        round(speed, 2),
                        "Mbps"
                    )

                break

            # ---------------- INVALID ----------------

            else:

                conn.sendall(b"INVALID_COMMAND\n")

    except Exception as e:

        print("[ERROR]", e)

    finally:

        conn.close()

        print("[CONNECTION] Closed")


# ================= SERVER =================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind((HOST, PORT))
server.listen()

print()
print("========================================")
print("   CONCURRENT MEASUREMENT SERVER")
print("========================================")
print("Host:", HOST)
print("Port:", PORT)
print()

while True:

    conn, addr = server.accept()

    thread = threading.Thread(
        target=handle_client,
        args=(conn, addr)
    )

    thread.start()