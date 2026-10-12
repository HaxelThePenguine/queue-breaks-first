# Engine and replay

## Matching

`MatchingEngine` is a single-instrument, in-memory book. Prices and quantities are positive integers; the engine does not assign a currency or tick size. Order IDs are integers, unique for the lifetime of the book. A cancelled or completed order ID cannot be submitted again. Signed IDs are supported for anonymous replay liquidity.

| Method | Behavior |
| --- | --- |
| `submit(id, side, quantity, price=None, time_in_force="GTC")` | Match at best price, then FIFO; return immutable fills and remaining quantities |
| `cancel(id, quantity=None)` | Remove part or all of a resting order |
| `replace(id, quantity, price=None)` | Set new total remaining quantity; reduction at the same price keeps priority |
| `order(id)` | Immutable remaining order, or `None` |
| `snapshot(depth=None)` | Aggregated bids descending and asks ascending |
| `add_resting(id, side, quantity, price)` | Historical insertion without matching |
| `execute_resting(id, quantity)` | Apply a feed execution to its reported resting order |

Sides are `buy` and `sell`. Limit orders support `GTC`, `IOC`, `FOK` and `POST_ONLY`. Market orders are IOC; an omitted/default GTC is converted to IOC. Market FOK and post-only requests are rejected.

FOK returns a fully cancelled result if executable liquidity is insufficient, without changing resting orders. A crossing post-only order raises `ValueError`. Invalid input leaves the book unchanged. Missing resting IDs raise `KeyError`. Increasing size or repricing a replacement moves it to the back of its new queue and can trigger matching.

`ExecutionResult.remaining_quantity` is the unfilled quantity, including both resting and cancelled quantity. Each fill records maker/taker IDs, maker side, integer price and quantity. Historical insertion and targeted execution bypass normal matching; use them only for reconstruction. The engine is single-threaded and does not implement venue-specific auctions, hidden orders, self-trade prevention or network latency.

## Order CSV

```csv
action,order_id,side,quantity,price,time_in_force
submit,1,sell,100,10100,GTC
submit,2,sell,50,10100,GTC
cancel,2,,10,,
replace,1,,80,10100,
submit,3,buy,120,,IOC
```

```bash
python scripts/match_orders.py --input orders.csv --output reports/matches.json
```

The report includes command results, trades, total executed quantity, volume-weighted execution price and the final book. Prices stay in the input units.

## Historical replay

```bash
python scripts/replay_book.py --source demo --strict
python scripts/replay_book.py --source lobster --ticker AAPL
python scripts/replay_book.py --message messages.csv --orderbook book.csv --levels 10
```

The first snapshot is already post-event and becomes the initial anonymous book. Its message is not applied twice. Subsequent records preserve file order, including timestamp ties.

Visible submissions, cancellations, deletions and executions use reported order IDs. Hidden executions do not change displayed liquidity. Auction records require a snapshot rebuild in normal mode and fail in strict mode. Halt status -1 stops trading, 0 resumes quoting, and 1 resumes trading; strict replay rejects visible executions during a tracked halt.

Normal mode keeps the supplied finite window. Unknown-ID removals reduce anonymous liquidity first, then observed orders if necessary. Newly exposed outer levels are seeded from the supplied snapshot, and outgoing levels are removed. These are explicit reconstruction assumptions, not recovered FIFO identities. Strict mode retains already known deeper liquidity and fails on unknown removals, inconsistent order quantities or any unmatched top-depth snapshot.

Summary counters:

- `seeded_rows`: the initial snapshot; normally one.
- `applied_events`: visible events reproduced through observed identities after the seed.
- `unknown_order_events` / `inferred_removal_quantity`: events without an available order identity and shares removed under the anonymous-first rule.
- `conflicting_order_events`: messages inconsistent with a known order.
- `unexplained_removal_quantity`: reported unknown-ID removals exceeding the quantity available at an observed price.
- `snapshot_mismatches`: unexplained differences before repair within observable depth, excluding normal outer-level entries/exits and auction resets.
- `reconciliations`: side-price adjustments from snapshots, including finite-window changes.
- `depth_entries` / `depth_exits`: levels seeded or retired during reconciliation.
- Hidden executions, auctions and trading-status counters refer to processed records after the initial seed.

Only the first 20 diagnostics are retained. Reports are bounded in size; the replay does not store a copy of every book. A zero mismatch count means the aggregate path agrees under these assumptions, not that all FIFO identities are known or that injected strategy orders would leave the market unchanged.

Format: [LOBSTER output](https://data.lobsterdata.com/info/DataStructure.php).
