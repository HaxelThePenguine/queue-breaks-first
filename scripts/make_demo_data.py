"""Regenerate the synthetic LOBSTER pair from a deterministic order lifecycle."""

from __future__ import annotations

import csv
from pathlib import Path

from queue_breaks_first.engine import MatchingEngine

ROOT = Path(__file__).resolve().parents[1]


def demo_rows():
    engine = MatchingEngine()
    for offset in range(3):
        engine.add_resting(1 + offset, "buy", 500 + 100 * offset, 1_000_000 - 100 * offset)
        engine.add_resting(4 + offset, "sell", 500 + 100 * offset, 1_000_300 + 100 * offset)
    messages, books = [], []

    def record(time, event_type, order_id, size, price, side):
        messages.append([time, event_type, order_id, size, price, 1 if side == "buy" else -1])
        snapshot = engine.snapshot(depth=3)
        bids, asks = snapshot["bids"], snapshot["asks"]
        row = []
        for level in range(3):
            ask = asks[level] if level < len(asks) else (9_999_999_999, 0)
            bid = bids[level] if level < len(bids) else (-9_999_999_999, 0)
            row.extend([*ask, *bid])
        books.append(row)

    # The first row is a post-event seed; its initial order identities are unavailable.
    record(34200.0, 5, 0, 10, 1_000_200, "sell")
    for cycle in range(8):
        start = 34201.0 + cycle * 4
        order_id = 100 + cycle * 10
        actions = [
            (0.0, 1, order_id, 120, 1_000_100, "buy"),
            (0.0, 1, order_id + 1, 80, 1_000_100, "buy"),
            (0.2, 1, order_id + 2, 150, 1_000_200, "sell"),
            (0.4, 2, order_id, 20, 1_000_100, "buy"),
            (0.6, 4, order_id, 60, 1_000_100, "buy"),
            (0.8, 4, order_id, 40, 1_000_100, "buy"),
            (1.0, 4, order_id + 1, 30, 1_000_100, "buy"),
            (1.2, 3, order_id + 1, 50, 1_000_100, "buy"),
            (1.4, 2, order_id + 2, 50, 1_000_200, "sell"),
            (1.6, 4, order_id + 2, 100, 1_000_200, "sell"),
            (1.8, 1, order_id + 3, 90, 1_000_300, "sell"),
            (2.0, 3, order_id + 3, 90, 1_000_300, "sell"),
        ]
        for elapsed, event_type, oid, size, price, side in actions:
            if event_type == 1:
                engine.add_resting(oid, side, size, price)
            elif event_type == 4:
                engine.execute_resting(oid, size)
            else:
                engine.cancel(oid, size)
            record(round(start + elapsed, 6), event_type, oid, size, price, side)
    return messages, books


def main() -> None:
    messages, books = demo_rows()
    folder = ROOT / "data" / "demo"
    folder.mkdir(parents=True, exist_ok=True)
    for filename, rows in [("demo_message.csv", messages), ("demo_orderbook.csv", books)]:
        with (folder / filename).open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(rows)
    print(f"Wrote {len(messages)} synthetic events to {folder}")


if __name__ == "__main__":
    main()
