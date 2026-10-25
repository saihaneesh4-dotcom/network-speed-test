import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path


# Backend URL can be overridden with the BACKEND_URL environment variable.
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "http://127.0.0.1:5000"
).rstrip("/")

HEARTBEAT_INTERVAL_SECONDS = 5
PROBE_TIMEOUT_SECONDS = 2

SERVERS_FILE = Path(__file__).resolve().parent / "servers.json"


def load_servers():
    """Load the configured servers from servers.json."""
    with open(SERVERS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("servers", [])



def is_server_reachable(server):
    """Return average TCP probe latency in milliseconds, or None if unreachable."""
    host = server["host"]
    port = int(server.get("measurement_port", server.get("port")))

    latencies = []

    for _ in range(5):
        try:
            with socket.create_connection(
                (host, port),
                timeout=PROBE_TIMEOUT_SECONDS
            ) as sock:
                sock.settimeout(PROBE_TIMEOUT_SECONDS)

                start = time.perf_counter()
                sock.sendall(b"PROBE\n")

                response = sock.recv(1024).decode(
                    "utf-8",
                    errors="replace"
                ).strip()

                end = time.perf_counter()

                if response != "PROBE_ACK":
                    return None

                latencies.append((end - start) * 1000)

        except (OSError, KeyError, TypeError, ValueError):
            return None

    return sum(latencies) / len(latencies) if latencies else None
def send_backend_request(endpoint, payload):
    """Send a JSON POST request to the backend."""
    url = BACKEND_URL + endpoint
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5
        ) as response:
            response_body = response.read().decode(
                "utf-8",
                errors="replace"
            )

            if response_body:
                return json.loads(response_body)

            return {}

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(
            f"Backend rejected {endpoint}: "
            f"HTTP {error.code} - {details}"
        )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        print(f"Backend request failed for {endpoint}: {error}")

    return None


def register_server(server):
    """Register a reachable server with the backend."""
    payload = {
        "server_id": server["server_id"],
        "host": server["host"],
        "port": int(server.get("measurement_port", server.get("port"))),
        "location": server["location"]
    }

    return send_backend_request("/servers/register", payload)


def send_heartbeat(server):
    """Tell the backend that this server is still reachable."""
    payload = {"server_id": server["server_id"]}

    return send_backend_request("/servers/heartbeat", payload)



def synchronize_servers():
    """Probe configured servers, register them, and send heartbeats."""
    try:
        servers = load_servers()
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not load {SERVERS_FILE}: {error}")
        return

    if not servers:
        print("No servers found in servers.json.")
        return

    for server in servers:
        server_id = server.get("server_id", "unknown")
        latency = is_server_reachable(server)

        if latency is None:
            print(f"{server_id}: OFFLINE or probe failed.")
            continue

        registration = register_server(server)

        if registration is None:
            print(f"{server_id}: probe OK ({latency:.2f} ms), registration failed.")
            continue

        heartbeat = send_heartbeat(server)

        if heartbeat is None:
            print(f"{server_id}: probe OK ({latency:.2f} ms), but heartbeat failed.")
        else:
            print(
                f"{server_id}: ONLINE | "
                f"latency={latency:.2f} ms | heartbeat sent."
            )
def main():
    print("Server registry synchronizer started.")
    print(f"Backend: {BACKEND_URL}")
    print(f"Heartbeat interval: {HEARTBEAT_INTERVAL_SECONDS} seconds")
    print("Press Ctrl+C to stop.\n")

    while True:
        synchronize_servers()
        print(
            f"\nNext synchronization in "
            f"{HEARTBEAT_INTERVAL_SECONDS} seconds.\n"
        )
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer registry synchronizer stopped.")