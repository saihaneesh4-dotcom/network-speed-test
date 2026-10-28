
import socket
import json
import time

DISCOVERY_PORTS = [6000, 6001, 6002]
DISCOVERY_TIMEOUT = 2
BROADCAST_ADDRESS = "255.255.255.255"


def discover_servers(timeout=DISCOVERY_TIMEOUT):
    servers = []
    seen_servers = set()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.2)
        sock.bind(("", 0))

        for port in DISCOVERY_PORTS:
            sock.sendto(
                b"DISCOVER_SERVER",
                (BROADCAST_ADDRESS, port)
            )

        print("Searching for Mini-Ookla servers...")
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            try:
                data, address = sock.recvfrom(1024)
                response = json.loads(data.decode("utf-8"))

                if not isinstance(response, dict):
                    continue

                if "server_id" not in response or "port" not in response:
                    continue

                response["host"] = address[0]

                server_key = (
                    response["server_id"],
                    response["host"],
                    int(response["port"])
                )

                if server_key not in seen_servers:
                    seen_servers.add(server_key)
                    servers.append(response)
                    print(
                        f"Discovered {response['server_id']} "
                        f"at {response['host']}:{response['port']}"
                    )

            except socket.timeout:
                continue
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
                continue

    print(f"Discovery finished: {len(servers)} server(s) found.")
    return servers


if __name__ == "__main__":
    discovered = discover_servers()
    print("\nDiscovered servers:")
    for server in discovered:
        print(server)
