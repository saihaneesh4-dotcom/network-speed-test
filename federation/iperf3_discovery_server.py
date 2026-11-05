
import socket
import json
import os

DISCOVERY_PORT = 6100
IPERF3_PORT = 5201

# Use the Wi-Fi IP that other devices can reach.
ADVERTISED_HOST = os.getenv("IPERF3_ADVERTISED_HOST", "10.56.66.200")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", DISCOVERY_PORT))

        print(f"iperf3 discovery responder listening on UDP {DISCOVERY_PORT}")
        print(f"Advertising iperf3 server at {ADVERTISED_HOST}:{IPERF3_PORT}")

        while True:
            try:
                data, client_address = sock.recvfrom(2048)

                if data.strip() != b"DISCOVER_IPERF3":
                    continue

                response = {
                    "service": "iperf3",
                    "host": ADVERTISED_HOST,
                    "port": IPERF3_PORT
                }

                sock.sendto(
                    json.dumps(response).encode("utf-8"),
                    client_address
                )

                print(
                    f"Responded to {client_address[0]}:"
                    f"{client_address[1]}"
                )

            except OSError as error:
                print("Socket error:", error)


if __name__ == "__main__":
    main()
