
import socket
import json

HOST = "0.0.0.0"
UDP_PORT = 5002

SERVERS = [
    {
        "server_id": "server_01",
        "measurement_port": 5001,
        "location": "Server-A"
    },
    {
        "server_id": "server_02",
        "measurement_port": 5002,
        "location": "Server-B"
    },
    {
        "server_id": "server_03",
        "measurement_port": 5003,
        "location": "Server-C"
    }
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, UDP_PORT))

print("========================================")
print("       UDP DISCOVERY RESPONDER")
print("========================================")
print("Listening on UDP port:", UDP_PORT)

while True:
    try:
        data, address = sock.recvfrom(1024)
        message = data.decode().strip()

        if message == "DISCOVER_SERVER":
            print("Discovery request from:", address)

            for server in SERVERS:
                response = server.copy()
                response["host"] = address[0]

                sock.sendto(
                    json.dumps(response).encode(),
                    address
                )

                print("Sent:", response["server_id"])

    except (OSError, UnicodeDecodeError) as error:
        print("Error:", error)
