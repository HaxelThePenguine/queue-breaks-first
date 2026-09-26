"""Inspect an included demo pair or an official LOBSTER sample."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from queue_breaks_first.data import load_lobster_pair, load_lobster_zip, sample_price_spells

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["demo", "lobster"], default="demo")
    parser.add_argument("--ticker", choices=["AAPL", "AMZN", "GOOG", "INTC", "MSFT"], default="AAPL")
    args = parser.parse_args()

    if args.source == "demo":
        folder = ROOT / "data" / "demo"
        events = load_lobster_pair(folder / "demo_message.csv", folder / "demo_orderbook.csv")
    else:
        path = ROOT / "data" / "raw" / f"LOBSTER_SampleFile_{args.ticker}_2012-06-21_10.zip"
        if not path.exists():
            parser.error(f"Missing {path.name}. Run: python scripts/download_sample.py {args.ticker}")
        events = load_lobster_zip(path)

    observations = sample_price_spells(events)
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    prefix = "demo" if args.source == "demo" else args.ticker.lower()
    observations.to_csv(report_dir / f"{prefix}_price_spells.csv", index=False)

    view = events.iloc[: min(len(events), 3000)]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    axes[0].plot(view["time_seconds"], view["bid_price"] / 10000, label="Best bid", linewidth=0.8)
    axes[0].plot(view["time_seconds"], view["ask_price"] / 10000, label="Best ask", linewidth=0.8)
    axes[0].set_ylabel("Price ($)")
    axes[0].legend()
    axes[1].plot(view["time_seconds"], view["bid_size"], label="Bid queue", linewidth=0.7)
    axes[1].plot(view["time_seconds"], view["ask_size"], label="Ask queue", linewidth=0.7)
    axes[1].set_ylabel("Shares")
    axes[1].set_xlabel("Seconds after midnight")
    axes[1].legend()
    fig.savefig(report_dir / f"{prefix}_book.png", dpi=150)
    plt.close(fig)

    print(f"Book updates: {len(events):,}")
    print(f"Usable one-tick price spells: {len(observations):,}")
    if not observations.empty:
        print(f"Fraction of next moves upward: {observations['next_move_up'].mean():.3f}")
    print(f"Outputs: {report_dir}")


if __name__ == "__main__":
    main()
