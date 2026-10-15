# Which Queue Breaks First?

A FIFO matching engine and LOBSTER replay tool for limit order book research.

Limit and market orders, partial fills, cancellations, replacements, GTC, IOC, FOK and post-only. Prices and quantities are integers.

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
