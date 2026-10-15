# Which Queue Breaks First?

A FIFO matching engine and LOBSTER replay tool for limit order book research.

Prices and quantities are integers. Partial fills, cancellations and replacements are supported.

## Order types

**Limit orders** buy at a specified price or lower, or sell at a specified price or higher.

**Market orders** execute against the best available prices. Any quantity that cannot be filled immediately is cancelled.

Limit orders support four execution policies:

- **GTC — Good Till Cancelled:** execute available quantity and leave the remainder in the book until filled or cancelled.
- **IOC — Immediate Or Cancel:** execute available quantity immediately and cancel the remainder.
- **FOK — Fill Or Kill:** execute the full quantity immediately or cancel the entire order.
- **Post-only:** join the book without taking liquidity. The order is rejected if it would execute immediately.

Market orders always use IOC.

## Run

```bash
python -m pip install -e ".[dev]"
python scripts/match_orders.py
python scripts/replay_book.py --source demo --strict
python -m pytest
```

## Historical data

```bash
python scripts/download_sample.py AAPL
python scripts/replay_book.py --source lobster --ticker AAPL
```

Reports are saved in `reports/`. The demo is synthetic; historical replay reports missing order identities and depth adjustments explicitly.

[Engine and replay](docs/engine.md) · [Data](data/README.md)
