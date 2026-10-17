import socket
import json
import time

BROADCAST_PORT = 5002

def discover_servers(timeout=2):
    servers = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)

    message = "DISCOVER_SERVER"

    sock.sendto(
        message.encode(),
        ("<broadcast>", BROADCAST_PORT)
    )

    start = time.time()

    while time.time() - start < timeout:
        try:
            data, address = sock.recvfrom(1024)
            response = json.loads(data.decode())

            response["host"] = address[0]
            servers.append(response)

        except socket.timeout:
            continue

    sock.close()

    return servers

if __name__ == "__main__":
    servers = discover_servers()

    print("\nDiscovered servers:")

    for server in servers:
        print(server)