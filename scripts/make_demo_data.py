"""Regenerate the committed synthetic LOBSTER-shaped demonstration files."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rng = np.random.default_rng(20260926)
    folder = ROOT / "data" / "demo"
    folder.mkdir(parents=True, exist_ok=True)
    bid, ask = 1_000_000, 1_000_100
    q_bid, q_ask = 500, 500
    time = 34200.0
    messages = []
    books = []

    for event_id in range(1, 1201):
        time += float(rng.exponential(0.4))
        side = "bid" if rng.random() < 0.5 else "ask"
        add = rng.random() < 0.43
        amount = int(rng.choice([50, 100, 150, 200]))
        event_type = 1 if add else 4
        event_price = bid if side == "bid" else ask
        direction = 1 if side == "bid" else -1

        if side == "bid":
            q_bid += amount if add else -amount
            if q_bid <= 0:
                bid -= 100
                ask -= 100
                q_bid, q_ask = int(rng.integers(300, 901) // 50 * 50), int(rng.integers(300, 901) // 50 * 50)
        else:
            q_ask += amount if add else -amount
            if q_ask <= 0:
                bid += 100
                ask += 100
                q_bid, q_ask = int(rng.integers(300, 901) // 50 * 50), int(rng.integers(300, 901) // 50 * 50)

        messages.append([round(time, 6), event_type, event_id, amount, event_price, direction])
        books.append([ask, q_ask, bid, q_bid])

    for filename, rows in [("demo_message.csv", messages), ("demo_orderbook.csv", books)]:
        with (folder / filename).open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(rows)
    print(f"Wrote {len(messages)} synthetic events to {folder}")


if __name__ == "__main__":
    main()
