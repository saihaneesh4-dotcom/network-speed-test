
from federation.server_registry import get_servers
from federation.server_probe import probe_server


def discover_servers(timeout=2):
    """Discover configured Mini-Ookla servers using TCP probes."""
    servers = []

    print("Searching for Mini-Ookla servers...")

    try:
        configured_servers = get_servers()
    except (OSError, ValueError, KeyError) as error:
        print(f"Could not load server registry: {error}")
        return servers

    for server in configured_servers:
        try:
            latency = probe_server(server)

            if latency is not None:
                servers.append(server)
                print(
                    f"Discovered {server['server_id']} "
                    f"at {server['host']}:{server['port']} "
                    f"(RTT: {latency:.2f} ms)"
                )
            else:
                print(
                    f"{server.get('server_id', 'Unknown server')} "
                    "- unavailable"
                )

        except (KeyError, OSError, TypeError, ValueError) as error:
            print(
                f"Could not check "
                f"{server.get('server_id', 'Unknown server')}: {error}"
            )

    print(f"Discovery finished: {len(servers)} server(s) found.")
    return servers
