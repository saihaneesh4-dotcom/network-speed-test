import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 5002))
server.listen(5)

print("Server running on port 5002...")

while True:
    client, address = server.accept()

    message = client.recv(1024).decode()

    if message == "PROBE":
        client.send("PROBE_ACK".encode())

    client.close()