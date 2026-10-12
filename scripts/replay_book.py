"""Replay a LOBSTER pair and check each observed snapshot."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from queue_breaks_first.data import load_lobster_pair, load_lobster_zip
from queue_breaks_first.replay import replay_lobster

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["demo", "lobster"], default="demo")
    parser.add_argument("--ticker", type=str.upper,
                        choices=["AAPL", "AMZN", "GOOG", "INTC", "MSFT"], default="AAPL")
    parser.add_argument("--message", type=Path)
    parser.add_argument("--orderbook", type=Path)
    parser.add_argument("--levels", type=int, default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("reports/replay_summary.json"))
    args = parser.parse_args()
    if bool(args.message) != bool(args.orderbook):
        parser.error("--message and --orderbook must be supplied together")
    if args.levels is not None and args.levels < 1:
        parser.error("--levels must be positive")
    try:
        if args.message is not None:
            events = load_lobster_pair(args.message, args.orderbook, levels=args.levels)
        elif args.source == "demo":
            folder = ROOT / "data" / "demo"
            events = load_lobster_pair(folder / "demo_message.csv", folder / "demo_orderbook.csv",
                                      levels=args.levels)
        else:
            path = ROOT / "data" / "raw" / f"LOBSTER_SampleFile_{args.ticker}_2012-06-21_10.zip"
            if not path.exists():
                parser.error(f"Missing {path.name}. Run: python scripts/download_sample.py {args.ticker}")
            events = load_lobster_zip(path, levels=args.levels)
        result = replay_lobster(events, strict=args.strict)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    summary = asdict(result.summary)
    summary["mode"] = "strict" if args.strict else "reconciled"
    summary["levels"] = (len(events.columns) - 6) // 4
    summary["start_time_seconds"] = float(events["time_seconds"].iloc[0])
    summary["end_time_seconds"] = float(events["time_seconds"].iloc[-1])
    summary["event_counts"] = {str(int(key)): int(value)
                               for key, value in events["event_type"].value_counts().sort_index().items()}
    summary["visible_execution_quantity"] = int(events.loc[events["event_type"] == 4, "event_size"].sum())
    summary["hidden_execution_quantity"] = int(events.loc[events["event_type"] == 5, "event_size"].sum())
    summary["final_book"] = result.engine.snapshot(depth=summary["levels"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
