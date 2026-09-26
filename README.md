# Which Queue Breaks First?

An open-source Python research project on limit order book dynamics and the direction of the next mid-price move.

## Objective

The project studies whether the sizes of the best bid and ask queues contain information about the direction of the next nonzero mid-price change. It combines an empirical queue-imbalance baseline with a stochastic model of queue depletion.

For best-quote sizes $Q_t^{\mathrm{bid}}$ and $Q_t^{\mathrm{ask}}$, the initial predictor is

$$
I_t = \frac{Q_t^{\mathrm{bid}} - Q_t^{\mathrm{ask}}}
           {Q_t^{\mathrm{bid}} + Q_t^{\mathrm{ask}}}.
$$

The mathematical model represents bid and ask liquidity as two interacting queues. Its key quantity is the probability $h(q_b,q_a)$ that the ask queue depletes before the bid queue. In a finite-state continuous-time Markov model, this probability satisfies

$$
\mathcal{L}h(q_b,q_a)=0,\qquad
h(q_b,0)=1,\quad h(0,q_a)=0,
$$

where $\mathcal{L}$ is the process generator. The empirical and stochastic estimates will be compared on out-of-sample price moves.

## Project components

| Component | Scope | Status |
| --- | --- | --- |
| Data ingestion | Load aligned LOBSTER message and orderbook files; retain best quotes and sizes | Implemented |
| Event sampling | Create one labeled observation per constant-mid-price spell | Implemented |
| Exploratory analysis | Inspect quotes, queue sizes, spreads, and observed price moves | Initial script available |
| Queue imbalance baseline | Estimate and evaluate next-move probabilities from best-quote imbalance | Planned |
| Queue depletion model | Construct a finite-state generator and solve for first-depletion probabilities | Planned |
| Model validation | Compare probabilities, calibration, and sensitivity across assets and periods | Planned |

The planned work and evaluation criteria are listed in [`ROADMAP.md`](ROADMAP.md). The model modules currently define the intended interfaces; their estimators are not yet implemented.

## Data

The repository includes a deterministic **synthetic** LOBSTER-shaped dataset in `data/demo/` for pipeline checks. It is not exchange data. The research dataset is the [official LOBSTER sample](https://data.lobsterdata.com/info/DataSamples.php), which supplies aligned message and orderbook records. Raw provider files are downloaded into the Git-ignored `data/raw/` directory. See [`data/README.md`](data/README.md) for provenance and format details.

```bash
python scripts/download_sample.py AAPL
```

The free sample covers one trading day. Results from it are exploratory and do not establish stability across dates or market regimes.

## Reproduce the current pipeline

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[research,dev]"
python scripts/inspect_data.py --source demo
python scripts/download_sample.py AAPL
python scripts/inspect_data.py --source lobster --ticker AAPL
python -m pytest
```

The inspection script saves a chart and a table of labeled price spells in `reports/`. Generated reports and raw provider files are excluded from Git.

## Repository structure

```text
data/demo/                       Synthetic pipeline fixture
data/raw/                        Official sample ZIPs (downloaded, ignored)
scripts/download_sample.py       Sample download entry point
scripts/inspect_data.py          Exploratory analysis entry point
src/queue_breaks_first/data.py   Data loading and event sampling
src/queue_breaks_first/models.py Queue imbalance model interface
src/queue_breaks_first/ctmc.py   Queue depletion model interface
tests/                           Data pipeline tests
ROADMAP.md                       Research and implementation plan
```

## Methodology and limits

The current sampler uses one book state at the start of each constant-mid-price spell and labels it by the next change. This avoids counting many correlated updates with the same future outcome as independent examples. The default sample is restricted to a one-tick spread, where queue depletion has a clearer interpretation. Wider spreads also allow inside-spread orders to move the mid-price. LOBSTER prices are stored as integer dollar prices multiplied by 10,000; the loader preserves that representation.

Predicting the direction of a price move is distinct from demonstrating an executable trading edge. Any trading interpretation would require explicit treatment of queue priority, spread, fees, latency, and adverse selection.

## References

1. Cont & de Larrard, [*Price dynamics in a Markovian limit order market*](https://arxiv.org/abs/1104.4596).
2. Gould & Bonart, [*Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book*](https://arxiv.org/abs/1512.03492).
3. LOBSTER, [sample files](https://data.lobsterdata.com/info/DataSamples.php) and [output format](https://data.lobsterdata.com/info/DataStructure.php).
