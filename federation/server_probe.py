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

            sock.send("PROBE\n".encode())
            response = sock.recv(1024).decode()

            end = time.perf_counter()

            if response == "PROBE_ACK\n":
                latency = (end - start) * 1000
                latencies.append(latency)
            else:
                return None

        except:
            return None

        finally:
            sock.close()

    return sum(latencies) / len(latencies)