import socket

HOST = "10.20.15.133"
PORT = 5002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)

try:
    sock.sendto(b"DISCOVER_SERVER", (HOST, PORT))
    print(f"Discovery request sent to {HOST}:{PORT}")

    while True:
        data, address = sock.recvfrom(2048)
        print(f"Response from {address}: {data.decode()}")

except socket.timeout:
    print("No UDP response received within 3 seconds.")

finally:
    sock.close()