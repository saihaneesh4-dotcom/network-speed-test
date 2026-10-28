import socket
import json
import time

DISCOVERY_PORT = 6100
DISCOVERY_TIMEOUT = 3
TARGET_ADDRESS = "255.255.255.255"


def discover_iperf3_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        sock.bind(("", 0))

        sock.sendto(
            b"DISCOVER_IPERF3",
            (TARGET_ADDRESS, DISCOVERY_PORT)
        )

        print("Searching for iperf3 server...")
        start = time.monotonic()

        while time.monotonic() - start < DISCOVERY_TIMEOUT:
            try:
                data, address = sock.recvfrom(2048)
                info = json.loads(data.decode("utf-8"))

                if info.get("service") != "iperf3":
                    continue

                return {
                    "host": address[0],
                    "port": int(info["port"])
                }

            except socket.timeout:
                continue
            except (ValueError, KeyError, UnicodeDecodeError):
                continue

    return None


if __name__ == "__main__":
    print(discover_iperf3_server())