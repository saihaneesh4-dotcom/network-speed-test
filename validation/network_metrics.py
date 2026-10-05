import subprocess
import re
import statistics


def measure_ping(host, count=10):
    command = ["ping", "-n", str(count), host]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = result.stdout

    times = []

    for line in output.splitlines():
        match = re.search(r"time[=<]\s*(\d+)ms", line)

        if match:
            times.append(float(match.group(1)))

    if not times:
        return None

    differences = [
    abs(times[i] - times[i - 1])
    for i in range(1, len(times))
]

    jitter = statistics.mean(differences) if differences else 0

    return {
    "latency_ms": statistics.mean(times),
    "jitter_ms": jitter,
    "packet_loss_percent": ((count - len(times)) / count) * 100,
    "samples": times
}


if __name__ == "__main__":
    host = "10.14.221.227"

    result = measure_ping(host)

    if result is None:
        print("No successful ping measurements.")
    else:
        print(f"Samples: {result['samples']}")
        print(f"Average latency: {result['latency_ms']:.2f} ms")
        print(f"Jitter: {result['jitter_ms']:.2f} ms")
        print(f"Packet loss: {result['packet_loss_percent']:.2f}%")