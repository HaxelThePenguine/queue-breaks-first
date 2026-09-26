# Learning path

The repository is intentionally incomplete. Work through these milestones in order and make a small commit after each one.

## 1. Inspect the book

Run `python scripts/inspect_data.py --source demo`, then repeat with `--source lobster --ticker AAPL`. Read `data.py` and check that message and orderbook rows align. Compare the distribution of bid and ask queue sizes, spreads, and the time between mid-price changes.

**Question:** why does an inside-spread limit order complicate the simple queue-depletion story?

## 2. Implement queue imbalance

Complete `queue_imbalance()` in `models.py`. Use the formula in the README. Decide how to handle zero total size, scalar inputs, and arrays. Add your own tests for equal queues, bid-heavy queues, ask-heavy queues, and invalid inputs.

Plot empirical `P(next move up | imbalance bin)` for the real sample. Give each price spell one vote.

## 3. Fit a simple benchmark

Use chronological training and test segments; do not shuffle events. Fit a logistic regression using imbalance only. Compare it with the constant-probability predictor estimated on the training segment. Report sample counts, ROC AUC, Brier score, and a calibration plot. Do not tune on the test segment.

**Question:** does a one-day result say anything about other days?

## 4. Build the stochastic model

Implement `build_generator()` and `up_move_probability()` in `ctmc.py`. Begin with a finite grid of queue sizes from 1 to `max_queue`. At each side, a limit order adds one unit at rate $\lambda$, while a market order or cancellation removes one unit at rate $\mu$. Set $h(q_b,0)=1$ and $h(0,q_a)=0$ and solve the resulting sparse linear system.

Write tests for symmetry, boundary conditions, probabilities in `[0,1]`, and the direction of the effect when one queue is made larger. Then compare your result with Monte Carlo simulation.

**Model limitation:** real orders have varying sizes and event rates depend on book state. The unit-jump, constant-rate model is a useful first model, not a literal description of every LOBSTER event.

## 5. Extend carefully

Estimate rates from order events, consider queue-size-dependent rates, and compare the model's predicted probabilities with held-out observations. Document each approximation. A multi-day dataset would make this extension much more meaningful.

## Suggested first issue

> Implement `queue_imbalance()` and add a plot of empirical next-move probability by imbalance decile, using one observation per price spell.
