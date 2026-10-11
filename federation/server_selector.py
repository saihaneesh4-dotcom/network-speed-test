from server_registry import get_servers
from server_probe import probe_server


def select_best_server():

    servers = get_servers()

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
            print(
                server["server_id"],
                "- unavailable"
            )

    if best_server is not None:

        selected_server = best_server.copy()

        selected_server["selection_latency_ms"] = round(
            best_latency,
            3
        )

        return selected_server

    return None


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
            round(
                selected["selection_latency_ms"],
                3
            ),
            "ms"
        )

    else:

        print("No servers are available")