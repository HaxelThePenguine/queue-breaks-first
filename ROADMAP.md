# Research roadmap

## Phase 1 — Data characterization

Characterize the distribution of best bid and ask queue sizes, spreads, mid-price changes, and intervals between changes. Confirm alignment between message and orderbook rows and document the filtering rules used to define a price-move observation.

**Deliverables:** descriptive figures, sample counts, and a documented event-selection procedure.

## Phase 2 — Empirical queue-imbalance model

Implement the queue-imbalance statistic in `models.py` and estimate the conditional probability of an upward next move. Compare an imbalance-based logistic regression with a constant-probability baseline. Use chronological train/test partitions and report ROC AUC, Brier score, and calibration.

**Deliverables:** tested imbalance function, fitted baseline, probability calibration plot, and out-of-sample metrics.

## Phase 3 — Queue depletion model

Implement the finite two-queue birth-death process in `ctmc.py`. For queue state $(q_b,q_a)$, solve the generator equation with absorbing boundaries at $q_a=0$ and $q_b=0$. Document the upper-boundary treatment and the rate assumptions. Verify symmetry and probability bounds, then compare the numerical solution with Monte Carlo estimates.

**Deliverables:** sparse generator, first-depletion probability solver, numerical verification, and a probability surface over queue states.

## Phase 4 — Empirical comparison

Estimate model inputs from order events, state the approximations required to map variable-sized orders to the finite-state process, and compare predicted probabilities with held-out book observations. Evaluate sensitivity to queue-size discretization, spread filtering, and the choice of asset.

**Deliverables:** model comparison, sensitivity analysis, and a discussion of failure modes.

## Research constraints

- The included synthetic data are used only to verify the pipeline.
- A single LOBSTER sample day supports an exploratory case study, not a general performance claim.
- Overlapping book updates are not treated as independent labels.
- Prediction quality and trading profitability are evaluated as separate questions.
