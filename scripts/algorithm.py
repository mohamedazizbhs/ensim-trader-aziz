
import json
import math
import requests
from datetime import datetime, timezone

from pathlib import Path

# ==================================================
# ENSIM TRADE CENTER - TRADING ALGORITHM
# ==================================================

# Official ENSIM market data
MARKET_URL = (
    "https://raw.githubusercontent.com/"
    "exofri/ensim-trade-center/main/"
    "docs/data/market.json"
)

# Personal ENSIM portfolio
HOLDINGS_URL = (
    "https://raw.githubusercontent.com/"
    "exofri/ensim-trade-center/main/"
    "traders/aziz/holdings.json"
)

# Strategy parameters
SHORT_WINDOW = 5
LONG_WINDOW = 12
TREND_WINDOW = 30
THRESHOLD = 0.01

# Risk management
MIN_MONEY_RESERVE = 50.0
MAX_BUY_SHARE = 0.20

# One signal unit represents 100 product units
SIGNAL_UNIT_SIZE = 100


# ==================================================
# 1. DATA ACQUISITION
# ==================================================

def fetch_json(url):
    response = requests.get(
        url,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def fetch_market():
    return fetch_json(MARKET_URL)


def fetch_holdings():
    return fetch_json(HOLDINGS_URL)


# ==================================================
# 2. TRADING STRATEGY
# ==================================================

def compute_signal(prices):
    """
    Trading strategy using moving averages.

    MM5: Short-term trend
    MM12: Medium-term trend
    MM30: Long-term trend filter

    Returns:
        +0.5 = BUY
        -0.5 = SELL
         0.0 = HOLD
    """

    if len(prices) < TREND_WINDOW:
        return 0.0

    short_avg = (
        sum(prices[-SHORT_WINDOW:])
        / SHORT_WINDOW
    )

    long_avg = (
        sum(prices[-LONG_WINDOW:])
        / LONG_WINDOW
    )

    trend_avg = (
        sum(prices[-TREND_WINDOW:])
        / TREND_WINDOW
    )

    current_price = prices[-1]

    if long_avg <= 0 or trend_avg <= 0:
        return 0.0

    difference = (
        short_avg - long_avg
    ) / long_avg

    # BUY: Confirmed upward trend
    if (
        difference > THRESHOLD
        and current_price > trend_avg
    ):
        return 0.5

    # SELL: Downward trend
    if (
        difference < -THRESHOLD
        or current_price < trend_avg
    ):
        return -0.5

    # HOLD: No trading condition met
    return 0.0


# ==================================================
# 3. RISK MANAGEMENT
# ==================================================

def secure_signal(signal, price, money, quantity):
    """
    Adjust trading signals according to:
    - Available money
    - Minimum cash reserve
    - Maximum buy budget
    - Owned quantity
    """

    if not all(
        math.isfinite(value)
        for value in (signal, price, money, quantity)
    ):
        raise ValueError("Invalid trading values.")

    if price <= 0:
        return 0.0

    # No trade
    if signal == 0:
        return 0.0

    # BUY
    if signal > 0:

        # Keep a minimum cash reserve
        available_money = max(
            0.0,
            money - MIN_MONEY_RESERVE
        )

        # Spend at most 20% of remaining cash
        max_budget = min(
            available_money,
            max(0.0, money) * MAX_BUY_SHARE
        )

        # Maximum affordable units
        max_units = max_budget / price

        # Units requested by strategy
        requested_units = signal * SIGNAL_UNIT_SIZE

        # Final permitted quantity
        allowed_units = min(
            requested_units,
            max_units
        )

        # Convert quantity back to signal.
        # Round down to avoid exceeding the budget.
        safe_signal = (
            math.floor(
                allowed_units / SIGNAL_UNIT_SIZE
                * 1000 + 1e-9
            ) / 1000
        )

        return max(0.0, safe_signal)

    # SELL
    if signal < 0:

        requested_units = (
            abs(signal) * SIGNAL_UNIT_SIZE
        )

        # Never sell more than owned
        allowed_units = min(
            requested_units,
            max(0.0, quantity)
        )

        safe_signal = (
            math.floor(
                allowed_units / SIGNAL_UNIT_SIZE
                * 1000 + 1e-9
            ) / 1000
        )

        return -max(0.0, safe_signal)

    return 0.0


# ==================================================
# 4. MAIN PROGRAM
# ==================================================

def main():

    print("=" * 50)
    print("ENSIM TRADE CENTER")
    print("SECURE TRADING SIMULATION")
    print("=" * 50)

    # Fetch market data
    print("\nFetching ENSIM market data...")
    market = fetch_market()

    # Fetch personal portfolio
    print("Fetching personal holdings...")
    holdings = fetch_holdings()

    products = market["products"]
    history = market["history"]

    print(f"\nProducts: {products}")
    print(f"History: {len(history)} observations")

    # Validate portfolio information
    remaining_money = float(holdings["money"])

    remaining_quantities = {
        product: float(quantity)
        for product, quantity
        in holdings["products"].items()
    }

    if (
        not math.isfinite(remaining_money)
        or remaining_money < 0
    ):
        raise ValueError("Invalid cash balance.")

    for product in products:
        quantity = remaining_quantities.get(
            product, 0.0
        )
        if not math.isfinite(quantity) or quantity < 0:
            raise ValueError(
                f"Invalid quantity for {product}"
            )

    print(
        f"\nAvailable money: "
        f"{remaining_money:.2f}"
    )

    print("\nCurrent holdings:")

    for product in products:
        print(
            f"  {product}: "
            f"{remaining_quantities.get(product, 0.0):.2f}"
        )

    # ==================================================
    # 5. CALCULATE SECURED TRADING DECISIONS
    # ==================================================

    decisions = {}

    print("\nTRADING DECISIONS")
    print("-" * 50)

    for product in products:

        # Historical prices
        prices = [
            float(row[product])
            for row in history
            if row.get(product) is not None
        ]

        # Check history
        if not prices:
            print(
                f"{product}: No price data. HOLD."
            )
            decisions[product] = 0.0
            continue

        # Original strategy signal
        raw_signal = compute_signal(prices)

        # Current product price
        current_price = prices[-1]

        # Owned product quantity
        quantity_owned = (
            remaining_quantities.get(product, 0.0)
        )

        # Apply risk controls
        signal = secure_signal(
            raw_signal,
            current_price,
            remaining_money,
            quantity_owned
        )

        # Save simulated decision
        decisions[product] = signal

        # Calculate units
        units = signal * SIGNAL_UNIT_SIZE

        # Update simulated remaining budget
        remaining_money -= units * current_price

        # Update simulated quantities
        remaining_quantities[product] = (
            quantity_owned + units
        )

        # Determine action
        if signal > 0:
            action = "BUY"

        elif signal < 0:
            action = "SELL"

        else:
            action = "HOLD"

        print(
            f"\nProduct {product}"
            f"\n  Price: {current_price:.4f}"
            f"\n  Original signal: {raw_signal:+.3f}"
            f"\n  Secured signal: {signal:+.3f}"
            f"\n  Action: {action}"
            f"\n  Units: {abs(units):.2f}"
        )

    # ==================================================
    # 6. SAVE SIMULATION
    # ==================================================

    output = Path(
        "simulation_decision.json"
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            decisions,
            f,
            indent=2
        )

    print("\n" + "=" * 50)
    print("SIMULATION COMPLETED")
    print("=" * 50)

    print(
        f"\nSimulation saved to: {output}"
    )

    print(
        f"Simulated remaining money: "
        f"{remaining_money:.2f}"
    )

    print(
        "\nNo real market decisions "
        "were changed."
    )
    
    # Keep a trace of simulated trading decisions
    log_dir = Path("output")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "decision_log.jsonl"
    
    log_entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "mode": "simulation",
            "market_observations": len(history),
            "decisions": decisions,
            "remaining_cash_simulated": round(
                remaining_money, 2
            )
        }
    
    with log_file.open(
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(log_entry) + "\n"
            )
    
    print(f"Decision log saved to: {log_file}")
    

# ==================================================
# PROGRAM ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
