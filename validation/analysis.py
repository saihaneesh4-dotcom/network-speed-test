import csv
import statistics
from pathlib import Path


RESULT_FILE = Path("results/iperf3_results.csv")


def load_results():
    with open(RESULT_FILE, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def analyze(values):
    return {
        "mean": statistics.mean(values),
        "minimum": min(values),
        "maximum": max(values),
        "std_dev": statistics.stdev(values),
        "range": max(values) - min(values),
    }


results = load_results()


normal_1_stream = [
    float(row["receiver_mbps"])
    for row in results
    if row["streams"] == "1" and row["option"] == "normal"
]

normal_4_stream = [
    float(row["receiver_mbps"])
    for row in results
    if row["streams"] == "4" and row["option"] == "normal"
]

slow_start = [
    float(row["receiver_mbps"])
    for row in results
    if row["option"] == "-O 3"
]


for name, values in [
    ("1 Stream", normal_1_stream),
    ("4 Streams", normal_4_stream),
    ("Slow Start Omission (-O 3)", slow_start),
]:
    stats = analyze(values)

    print(f"\n{name}")
    print("-" * 35)
    print(f"Trials: {values}")
    print(f"Mean: {stats['mean']:.2f} Mbps")
    print(f"Minimum: {stats['minimum']:.2f} Mbps")
    print(f"Maximum: {stats['maximum']:.2f} Mbps")
    print(f"Standard deviation: {stats['std_dev']:.2f} Mbps")
    print(f"Range: {stats['range']:.2f} Mbps")