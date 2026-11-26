
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "exofri/ensim-trade-center/main"
)

TRADERS = {
    "Mon trader": "aziz",
    "Random Trader": "random_trader",
    "Random Buyer": "random_buyer",
    "Random Seller": "random_seller"
}


def fetch_json(path):
    response = requests.get(
        f"{BASE_URL}/{path}",
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def main():
    market = fetch_json("docs/data/market.json")
    history = market["history"]

    # Latest available price for each product
    prices = {}

    for product in ("A", "B", "C"):
        values = [
            float(row[product])
            for row in history
            if row.get(product) is not None
        ]

        if not values:
            raise ValueError(
                f"No price data for {product}"
            )

        prices[product] = values[-1]

    comparison = []

    print("\nENSIM - PORTFOLIO COMPARISON")
    print("-" * 60)

    for name, trader_id in TRADERS.items():
        holdings = fetch_json(
            f"traders/{trader_id}/holdings.json"
        )

        cash = float(holdings["money"])

        positions = {
            p: float(holdings["products"].get(p, 0))
            for p in prices
        }

        assets_value = sum(
            positions[p] * prices[p]
            for p in prices
        )

        total = cash + assets_value

        comparison.append({
            "name": name,
            "trader_id": trader_id,
            "cash": round(cash, 2),
            "assets_value": round(assets_value, 2),
            "total_value": round(total, 2)
        })

        print(
            f"{name:16} | "
            f"Cash: {cash:10.2f} | "
            f"Total: {total:12.2f}"
        )

    result = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "prices": prices,
        "comparison": comparison
    }

    output = Path(
        "docs/data/portfolio_comparison.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved to: {output}")


if __name__ == "__main__":
    main()
