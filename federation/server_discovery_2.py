import socket
import json

HOST = "0.0.0.0"
DISCOVERY_PORT = 6001

SERVER_INFO = {
    "server_id": "server_02",
    "port": 5002,
    "location": "Vellore"
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, DISCOVERY_PORT))

print(f"UDP discovery responder running on port {DISCOVERY_PORT}")

while True:
    data, address = sock.recvfrom(1024)
    message = data.decode().strip()

    if message == "DISCOVER_SERVER":
        response = json.dumps(SERVER_INFO).encode()
        sock.sendto(response, address)
        print(f"Discovery request from {address}")