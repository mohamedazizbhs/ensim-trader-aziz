
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SIMULATION_FILE = ROOT / "simulation_decision.json"
DECISION_FILE = ROOT / "decision.json"

PRODUCTS = ("A", "B", "C")


def main():
    if not SIMULATION_FILE.exists():
        raise FileNotFoundError(
            "Run scripts/algorithm.py first."
        )

    with SIMULATION_FILE.open(
        "r", encoding="utf-8"
    ) as file:
        simulation = json.load(file)

    decisions = {}

    for product in PRODUCTS:
        if product not in simulation:
            raise ValueError(
                f"Missing signal for product {product}"
            )

        signal = float(simulation[product])

        if not math.isfinite(signal) or not -1 <= signal <= 1:
            raise ValueError(
                f"Invalid signal for {product}: {signal}"
            )

        decisions[product] = signal

    print("\nENSIM - DECISION PUBLICATION")
    print("-" * 40)

    for product, signal in decisions.items():
        action = (
            "BUY" if signal > 0
            else "SELL" if signal < 0
            else "HOLD"
        )

        print(
            f"{product}: {action} "
            f"({signal:+.3f})"
        )

    print(
        "\nWARNING: Publishing decision.json "
        "to GitHub makes these orders available "
        "to the ENSIM simulator."
    )

    confirmation = input(
        "\nType PUBLISH to update decision.json: "
    )

    if confirmation != "PUBLISH":
        print("Cancelled. No changes made.")
        return

    decisions["updated_at"] = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    with DECISION_FILE.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            decisions,
            file,
            indent=2
        )

    print("\ndecision.json updated locally.")
    print(
        "Review the file before committing "
        "and pushing to GitHub."
    )


if __name__ == "__main__":
    main()
