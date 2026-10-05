import csv
import statistics
from pathlib import Path

RESULT_FILE = Path("results/iperf3_results.csv")

def load_iperf3_results():
    with open(RESULT_FILE, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def compare_throughput(engine_mbps, reference_mbps):
    if reference_mbps <= 0:
        raise ValueError("Reference throughput must be greater than 0.")

    difference_mbps = abs(engine_mbps - reference_mbps)
    percentage_difference = (difference_mbps / reference_mbps) * 100

    return {
        "engine_mbps": engine_mbps,
        "reference_mbps": reference_mbps,
        "difference_mbps": difference_mbps,
        "percentage_difference": percentage_difference
    }


def analyze_trials(engine_trials, reference_trials):
    if len(engine_trials) != len(reference_trials):
        raise ValueError("Both trial lists must contain the same number of trials.")

    if len(engine_trials) == 0:
        raise ValueError("Trial lists cannot be empty.")

    comparisons = []

    for engine, reference in zip(engine_trials, reference_trials):
        comparisons.append(
            compare_throughput(engine, reference)
        )

    percentage_errors = [
        result["percentage_difference"]
        for result in comparisons
    ]

    return {
        "comparisons": comparisons,
        "mean_percentage_error": statistics.mean(percentage_errors),
        "maximum_percentage_error": max(percentage_errors),
        "minimum_percentage_error": min(percentage_errors)
    }


if __name__ == "__main__":
    results = load_iperf3_results()

    iperf3_trials = [
        float(row["receiver_mbps"])
        for row in results
        if row["streams"] == "4" and row["option"] == "normal"
    ]

    print("iperf3 4-stream reference trials:")
    print(iperf3_trials)

    engine_trials = [33.0, 21.0, 29.0]

    result = analyze_trials(
        engine_trials,
        iperf3_trials
    )

    print("\nAarav Engine vs iperf3")
    print("-" * 35)

    for i, comparison in enumerate(result["comparisons"], start=1):
        print(f"\nTrial {i}")
        print(f"Engine: {comparison['engine_mbps']:.2f} Mbps")
        print(f"iperf3: {comparison['reference_mbps']:.2f} Mbps")
        print(f"Difference: {comparison['difference_mbps']:.2f} Mbps")
        print(
            f"Percentage difference: "
            f"{comparison['percentage_difference']:.2f}%"
        )

    print("\nOverall")
    print("-" * 35)
    print(
        f"Mean percentage error: "
        f"{result['mean_percentage_error']:.2f}%"
    )
    print(
        f"Maximum percentage error: "
        f"{result['maximum_percentage_error']:.2f}%"
    )
    print(
        f"Minimum percentage error: "
        f"{result['minimum_percentage_error']:.2f}%"
    )