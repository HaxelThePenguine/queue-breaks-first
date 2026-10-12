"""Match CSV order commands or run a small FIFO example."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path

from queue_breaks_first.engine import MatchingEngine

DEMO = [
    {"action": "submit", "order_id": "1", "side": "sell", "quantity": "100", "price": "1000100"},
    {"action": "submit", "order_id": "2", "side": "sell", "quantity": "80", "price": "1000100"},
    {"action": "submit", "order_id": "3", "side": "sell", "quantity": "150", "price": "1000200"},
    {"action": "submit", "order_id": "4", "side": "buy", "quantity": "200", "price": "1000000"},
    {"action": "cancel", "order_id": "2", "quantity": "20"},
    {"action": "submit", "order_id": "5", "side": "buy", "quantity": "210"},
]


def match_commands(commands):
    engine = MatchingEngine()
    results, trades = [], []
    for row_number, command in enumerate(commands, 1):
        try:
            action = command["action"].strip().lower()
            order_id = int(command["order_id"])
            quantity = int(command["quantity"]) if command.get("quantity") else None
            price = int(command["price"]) if command.get("price") else None
            if action == "submit":
                result = engine.submit(order_id, command["side"].strip().lower(), quantity, price,
                                       time_in_force=command.get("time_in_force") or "GTC")
            elif action == "replace":
                result = engine.replace(order_id, quantity, price)
            elif action == "cancel":
                cancelled = engine.cancel(order_id, quantity)
                results.append({"action": action, "order_id": order_id, "cancelled_quantity": cancelled})
                continue
            else:
                raise ValueError(f"Unknown action {action!r}")
            results.append({"action": action, "order_id": order_id, **asdict(result)})
            trades.extend(asdict(fill) for fill in result.fills)
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Command {row_number}: {exc}") from exc
    filled = sum(trade["quantity"] for trade in trades)
    return {
        "commands": len(results), "results": results, "trades": trades,
        "filled_quantity": filled,
        "average_price": sum(trade["price"] * trade["quantity"] for trade in trades) / filled if filled else None,
        "book": engine.snapshot(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="CSV: action,order_id,side,quantity,price,time_in_force")
    parser.add_argument("--output", type=Path, default=Path("reports/matching_summary.json"))
    args = parser.parse_args()
    try:
        if args.input is None:
            summary = match_commands(DEMO)
        else:
            with args.input.open(newline="", encoding="utf-8-sig") as handle:
                summary = match_commands(csv.DictReader(handle))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
