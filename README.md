# Which Queue Breaks First?

Limit order book research in Python. The current focus is a FIFO matching engine and historical replay. Queue depletion models come next.

## Run

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/match_orders.py
python scripts/replay_book.py --source demo --strict
python -m pytest
```

For the official ten-level AAPL sample:

```bash
python scripts/download_sample.py AAPL
python scripts/replay_book.py --source lobster --ticker AAPL
```

Raw data and generated reports are ignored by Git. The sample covers 21 June 2012; it is a replay check, not evidence of trading performance.

## Engine

The engine uses integer prices and quantities, price-time priority and the resting order's execution price. It supports limit and market orders, partial fills, cancellation, replacement, GTC, IOC, FOK and post-only orders.

```python
from queue_breaks_first.engine import MatchingEngine

book = MatchingEngine()
book.submit(1, "sell", 100, 10100)
book.submit(2, "sell", 50, 10100)
result = book.submit(3, "buy", 120, 10100)
print(result.fills)
print(book.snapshot())
```

At the same price, reducing an order keeps priority. Increasing its quantity or changing its price loses priority. Market orders never rest; FOK checks available liquidity before changing the book.

`scripts/match_orders.py --input orders.csv` accepts submit, cancel and replace commands. Run `--help` for options. [Engine and replay notes](docs/engine.md) describe the API and input format.

## Replay

LOBSTER message row k produces book row k. Replay starts from the first post-event snapshot, then applies the remaining messages in file order, including equal timestamps. Loading with `levels=None` retains all supplied depth; the original level-one loader remains the default.

The first snapshot has aggregate quantities, not a complete FIFO history. Levels entering the observed depth can also contain unseen orders. Normal replay reconciles this liquidity and reports the adjustments. `--strict` fails when an event or snapshot needs an unsupported reconstruction. It does not certify the initial anonymous queue's order priority.

Historical executions reference the resting order ID. They are applied as feed events, separately from matching a new incoming order. Hidden executions leave displayed depth unchanged; auctions and halts are handled separately.

The committed demo is synthetic and deterministic. It exercises order lifecycles and strict replay. [Data provenance](data/README.md) covers the official sample.

## Next

Finish the imbalance baseline and queue CTMC, then add state-dependent event sizes, queue-aware fill models and strategy evaluation. A matching engine alone does not estimate strategy capacity. The plan is in [ROADMAP.md](ROADMAP.md).

References: [LOBSTER format](https://data.lobsterdata.com/info/DataStructure.php), [Cont & de Larrard](https://arxiv.org/abs/1104.4596), [Gould & Bonart](https://arxiv.org/abs/1512.03492).
