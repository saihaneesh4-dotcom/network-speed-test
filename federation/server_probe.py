import socket
import time


def probe_server(server):

    host = server["host"]
    port = server["port"]

    latencies = []

    for i in range(5):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)

        try:
            sock.connect((host, port))

            start = time.perf_counter()

            sock.sendall(b"PROBE\n")

            response = sock.recv(1024).decode().strip()

            end = time.perf_counter()

            if response == "PROBE_ACK":
                latency = (end - start) * 1000
                latencies.append(latency)

            else:
                return None

        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

        finally:
            sock.close()

    if len(latencies) == 0:
        return None

    return sum(latencies) / len(latencies)