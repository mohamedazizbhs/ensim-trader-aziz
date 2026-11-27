
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "exofri/ensim-trade-center/main/"
)

TRADERS = {
    "Mon trader": "aziz",
    "Random Trader": "random_trader",
    "Random Buyer": "random_buyer",
    "Random Seller": "random_seller",
}

PRODUCTS = ("A", "B", "C")


def fetch_json(path):
    response = requests.get(
        BASE_URL + path,
        timeout=30
    )

    response.raise_for_status()
    return response.json()


def valid_number(value, label):
    number = float(value)

    if not math.isfinite(number) or number < 0:
        raise ValueError(
            f"Invalid {label}: {number}"
        )

    return number


def collect():
    market = fetch_json(
        "docs/data/market.json"
    )

    history = market["history"]

    if not history:
        raise ValueError(
            "Market history is empty"
        )

    prices = {}

    for product in PRODUCTS:
        values = [
            row[product]
            for row in history
            if row.get(product) is not None
        ]

        if not values:
            raise ValueError(
                f"No prices for product {product}"
            )

        prices[product] = valid_number(
            values[-1],
            f"price {product}"
        )

        if prices[product] == 0:
            raise ValueError(
                f"Zero price for {product}"
            )

    comparison = []

    for name, trader_id in TRADERS.items():

        portfolio = fetch_json(
            f"traders/{trader_id}/holdings.json"
        )

        cash = valid_number(
            portfolio["money"],
            f"cash {trader_id}"
        )

        positions = portfolio["products"]

        assets = sum(
            valid_number(
                positions.get(product, 0),
                f"quantity {trader_id}/{product}"
            ) * prices[product]
            for product in PRODUCTS
        )

        comparison.append({
            "name": name,
            "trader_id": trader_id,
            "cash": round(cash, 2),
            "assets_value": round(assets, 2),
            "total_value": round(
                cash + assets, 2
            )
        })

    return {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "market_observations": len(history),
        "prices": prices,
        "comparison": comparison
    }


def save(snapshot):
    data_dir = ROOT / "docs" / "data"

    data_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    comparison_path = (
        data_dir / "portfolio_comparison.json"
    )

    history_path = (
        data_dir / "portfolio_history.json"
    )

    if history_path.exists():
        with history_path.open(
            "r",
            encoding="utf-8"
        ) as f:
            history_data = json.load(f)

        snapshots = history_data["snapshots"]

        if not isinstance(snapshots, list):
            raise ValueError(
                "Invalid snapshots format"
            )
    else:
        snapshots = []

    # Only store genuinely new data
    is_new = (
        not snapshots
        or any(
            snapshots[-1].get(key) != snapshot[key]
            for key in (
                "market_observations",
                "prices",
                "comparison"
            )
        )
    )

    if is_new:
        snapshots.append(snapshot)

        with history_path.open(
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                {"snapshots": snapshots},
                f,
                indent=2,
                ensure_ascii=False
            )

    # Update latest comparison
    # only if market/portfolio data changed
    if is_new or not comparison_path.exists():
        latest_comparison = {
            "timestamp": snapshot["timestamp"],
            "prices": snapshot["prices"],
            "comparison": snapshot["comparison"]
        }

        with comparison_path.open(
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                latest_comparison,
                f,
                indent=2,
                ensure_ascii=False
            )

    print(
        "Market observations:",
        snapshot["market_observations"]
    )

    print(
        "Portfolio snapshots:",
        len(snapshots)
    )

    print(
        "New snapshot saved:",
        is_new
    )

    print("\nPORTFOLIO VALUES")

    for trader in snapshot["comparison"]:
        print(
            f"{trader['name']:<16}"
            f"{trader['total_value']:>14.2f}"
        )

    if not is_new:
        print(
            "\nNo new market or portfolio data."
        )


def main():
    snapshot = collect()
    save(snapshot)


if __name__ == "__main__":
    main()
