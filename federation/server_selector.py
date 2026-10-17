
import os
import sys
import json
import urllib.request
import urllib.error
import socket

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server_discovery import discover_servers
from server_probe import probe_server


REGISTRY_URL = os.environ.get(
    "SERVER_REGISTRY_URL",
    "http://10.56.66.133:5000/servers"
)


def get_servers_from_registry():
    request = urllib.request.Request(
        REGISTRY_URL,
        headers={"Accept": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=3) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("servers", [])


def get_available_server_list():
    discovered_servers = []

    try:
        registered_servers = get_servers_from_registry()

        for server in registered_servers:
            if server.get("status") != "online":
                continue

            discovered_servers.append({
                "server_id": server.get("server_id"),
                "host": server.get("host"),
                "measurement_port": server.get(
                    "measurement_port",
                    server.get("port")
                ),
                "location": server.get("location", "Unknown")
            })

        if discovered_servers:
            print("Using backend server registry.")
            return discovered_servers

        print("No online servers in backend registry.")
        print("Falling back to UDP discovery.")

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        AttributeError
    ) as error:
        print("Backend registry unavailable:", error)
        print("Falling back to UDP discovery.")

    try:
        discovered_servers = discover_servers(timeout=2)
    except (OSError, ValueError) as error:
        print("UDP discovery failed:", error)
        return []

    return discovered_servers


def select_best_server():
    discovered_servers = get_available_server_list()

    if not discovered_servers:
        print("No servers discovered.")
        return None

    servers = []
    seen = set()

    for discovered in discovered_servers:
        server_id = discovered.get("server_id")
        host = discovered.get("host")
        port = discovered.get(
            "measurement_port",
            discovered.get("port")
        )

        if not server_id or not host or port is None:
            continue

        try:
            port = int(port)
        except (TypeError, ValueError):
            continue

        if not 1 <= port <= 65535:
            continue

        key = (server_id, host, port)

        if key in seen:
            continue

        seen.add(key)

        servers.append({
            "server_id": server_id,
            "host": host,
            "port": port,
            "location": discovered.get("location", "Unknown")
        })

    if not servers:
        print("No valid servers discovered.")
        return None

    best_server = None
    best_latency = float("inf")

    for server in servers:
        latency = probe_server(server)

        if latency is not None:
            print(
                server["server_id"],
                "- Average RTT:",
                round(latency, 3),
                "ms"
            )

            if latency < best_latency:
                best_latency = latency
                best_server = server
        else:
            print(server["server_id"], "- unavailable")

    if best_server is None:
        print("No available measurement servers.")
        return None

    selected_server = best_server.copy()
    selected_server["selection_latency_ms"] = round(
        best_latency, 3
    )

    return selected_server


if __name__ == "__main__":
    selected = select_best_server()

    if selected is not None:
        print()
        print("Selected Server:", selected["server_id"])
        print("Host:", selected["host"])
        print("Port:", selected["port"])
        print("Location:", selected["location"])
        print(
            "Selection RTT:",
            selected["selection_latency_ms"],
            "ms"
        )
    else:
        print("No servers are available")
