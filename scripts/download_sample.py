"""Download one official LOBSTER depth-10 sample into the ignored raw folder."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve

TICKERS = {"AAPL", "AMZN", "GOOG", "INTC", "MSFT"}
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", type=str.upper, choices=sorted(TICKERS))
    args = parser.parse_args()
    filename = f"LOBSTER_SampleFile_{args.ticker}_2012-06-21_10.zip"
    destination = ROOT / "data" / "raw" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"Already available: {destination}")
        return
    url = f"https://php.lobsterdata.com/info/sample/{filename}"
    print(f"Downloading official sample: {url}")
    try:
        urlretrieve(url, destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    print(f"Saved: {destination}")


if __name__ == "__main__":
    main()
