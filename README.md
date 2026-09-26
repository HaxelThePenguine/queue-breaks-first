# Which Queue Breaks First?

A hands-on Python project about market microstructure, best bid/ask queues, and the direction of the next mid-price move.

> **Status:** learning scaffold. The data loader and exploratory script work; the predictive and stochastic models are intentionally left for you to implement.

## Research question

Given the visible size at the best bid and ask, can we estimate the probability that the **next nonzero mid-price move** is upward?

The project starts with queue imbalance:

$$
I_t = \frac{Q_t^{\mathrm{bid}} - Q_t^{\mathrm{ask}}}
           {Q_t^{\mathrm{bid}} + Q_t^{\mathrm{ask}}}.
$$

Then it moves to a two-queue birth-death model. If the ask queue reaches zero first, the model predicts an upward price move. For a state $q=(q_b,q_a)$, its hitting probability $h(q)$ satisfies

$$
\mathcal{L}h(q)=0,\qquad
h(q_b,0)=1,\quad h(0,q_a)=0,
$$

where $\mathcal{L}$ is the generator of the queue process. Building and solving this system is one of the main exercises.

## What is included

- A small **synthetic** LOBSTER-shaped data pair committed under `data/demo/`, so the project runs immediately.
- A loader for LOBSTER message/orderbook CSV pairs and the official sample ZIP archives.
- A data inspection script that produces a first plot and a table of price-move observations.
- Empty model functions with precise tasks and a guided learning path in [`LEARNING_PATH.md`](LEARNING_PATH.md).
- Tests for the completed data plumbing and a basic GitHub Actions workflow.

The synthetic files are for learning and plumbing checks only. They are not market observations and should not be used to claim empirical predictive performance.

## Quick start

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[research,dev]"
python scripts/inspect_data.py --source demo
python -m pytest
```

The inspection script writes a chart and observation CSV to `reports/`, which is ignored by Git.

## Use actual order book data

LOBSTER publishes [free sample files](https://data.lobsterdata.com/info/DataSamples.php) with aligned message and orderbook data. Download an official sample directly from the provider:

```bash
python scripts/download_sample.py AAPL
python scripts/inspect_data.py --source lobster --ticker AAPL
```

The command downloads the depth-10 sample ZIP into `data/raw/`. Raw provider data are kept out of this repository; the URL, source, and format are documented in [`data/README.md`](data/README.md). If the automated download fails, use the provider's sample page and place the ZIP in `data/raw/` with its original filename.

One sample day is useful for a prototype. It cannot establish stability across days, regimes, or stocks. A serious empirical study needs more dates and a chronological holdout.

## Project map

```text
data/demo/                       Tiny synthetic input data
data/raw/                        Official sample ZIPs (downloaded, ignored)
scripts/download_sample.py       Download a provider sample
scripts/inspect_data.py          Working exploratory entry point
src/queue_breaks_first/data.py   Working data loader and event sampler
src/queue_breaks_first/models.py Your first predictive model
src/queue_breaks_first/ctmc.py   Your queueing model
tests/                           Tests for completed plumbing
LEARNING_PATH.md                 Suggested sequence of exercises
```

## Methodological choices

The starter sampler takes **one observation at the start of each constant-mid-price spell** and labels it with the direction of the next change. This avoids treating hundreds of highly correlated book updates with the same future label as independent examples. The default analysis filters to a one-tick spread, where queue depletion has a clearer interpretation; price changes can also arise from inside-spread orders when the spread is wider. LOBSTER prices are integer units of $1/10{,}000; the loader preserves those integers.

Even a strong classifier would not establish a profitable trading strategy. Execution priority, spread, fees, latency, and adverse selection would need a separate study.

## Reading

1. Cont & de Larrard, [*Price dynamics in a Markovian limit order market*](https://arxiv.org/abs/1104.4596) — the queueing model and hitting probabilities.
2. Gould & Bonart, [*Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book*](https://arxiv.org/abs/1512.03492) — an empirical baseline.
3. LOBSTER, [sample files](https://data.lobsterdata.com/info/DataSamples.php) and [output format](https://data.lobsterdata.com/info/DataStructure.php).
