# Which Queue Breaks First?

A FIFO matching engine with historical LOBSTER replay. The best price fills first. At the same price, the oldest order goes first.

Prices and quantities are integers. The engine supports partial fills, cancellations and replacements.

## Order types

**Limit orders** buy at a specified price or lower, or sell at a specified price or higher.

**Market orders** execute at the best available prices and cancel any unfilled quantity (IOC).

Limit orders support four execution policies:

- **GTC — Good Till Cancelled:** execute available quantity and leave the remainder in the book until filled or cancelled.
- **IOC — Immediate Or Cancel:** execute available quantity immediately and cancel the remainder.
- **FOK — Fill Or Kill:** execute the full quantity immediately or cancel the entire order.
- **Post-only:** join the book without taking liquidity. The order is rejected if it would execute immediately.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python scripts/match_orders.py
python scripts/replay_book.py --source demo --strict
python -m pytest
```

The matching demo buys 210 units, taking 160 at the best ask in FIFO order and 50 at the next price. Both demos save JSON reports in `reports/`.

## Historical data

```bash
python scripts/download_sample.py AAPL
python scripts/replay_book.py --source lobster --ticker AAPL
```

The offline demo uses synthetic data. Historical replay reports missing order IDs and adjustments to the visible book.

## Progress

100 one-unit market orders against 100,000 one-unit orders at one price. Median of 5 runs, setup excluded. Both versions ran on the same machine with Python 3.12 on 2026-11-17.

| Version | Time/order | vs. baseline |
| --- | --- | --- |
| [Baseline · 623d8d7](https://github.com/HaxelThePenguine/queue-breaks-first/commit/623d8d7) | 1,354 µs | 1× |
| [Queue head · 91d2b85](https://github.com/HaxelThePenguine/queue-breaks-first/commit/91d2b85) | 2.7 µs | ~500× |

Run it with `python scripts/benchmark_queue.py`.

[Engine and replay](docs/engine.md) · [Data](data/README.md)
