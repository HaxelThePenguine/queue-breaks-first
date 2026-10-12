# Roadmap

## Engine and replay

FIFO matching, order lifecycles, multi-level loading and audited LOBSTER replay. Verify price-time priority, quantity conservation, atomic rejection and historical snapshot agreement. Keep initial and out-of-window liquidity assumptions visible in replay summaries.

## Queue models

Implement imbalance and a logistic next-move baseline. Use chronological train/test splits, Brier score and calibration.

Implement the sparse two-queue CTMC. Check absorbing boundaries, symmetry, truncation sensitivity and Monte Carlo agreement. Compare depletion times as well as move direction.

## Reactive simulation

Estimate event intensities and conditional sizes from counts and state residence times. Start with queue-reactive and SAQR models. Compare queue sizes, spreads, depletion times, waiting times and volatility before adding Hawkes or neural models.

## Execution and capacity

Add queue-aware fills, completion time, signed markouts, fees and latency. Evaluate a specified strategy across size, horizon and participation, reporting execution costs and net results with uncertainty.

Capacity needs a strategy and a calibrated market response. Historical replay supplies execution mechanics and observational checks; it does not identify the market's counterfactual response to large orders.

## Data

Synthetic data are for verification. The free LOBSTER sample supports an exploratory replay. Model validation needs several days and regimes, with time dependence respected in splits and uncertainty estimates.
