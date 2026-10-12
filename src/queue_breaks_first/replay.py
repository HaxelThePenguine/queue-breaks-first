"""Replay aligned LOBSTER messages against their post-event depth snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import pandas as pd

from .engine import MatchingEngine


class ReplayError(ValueError):
    """An event cannot be reproduced from the available visible orders."""


@dataclass
class ReplaySummary:
    rows: int = 0
    seeded_rows: int = 0
    applied_events: int = 0
    unknown_order_events: int = 0
    inferred_removal_quantity: int = 0
    unexplained_removal_quantity: int = 0
    conflicting_order_events: int = 0
    reconciliations: int = 0
    snapshot_mismatches: int = 0
    depth_entries: int = 0
    depth_exits: int = 0
    hidden_executions: int = 0
    auctions: int = 0
    halts: int = 0
    resume_events: int = 0
    quoting_resume_events: int = 0
    discrepancies: list[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    engine: MatchingEngine
    summary: ReplaySummary


def replay_lobster(events: pd.DataFrame, *, strict: bool = False) -> ReplayResult:
    """Reproduce the supplied finite depth, preserving input order for time ties.

    The first row is already a post-event state and is seeded anonymously.
    Reconciled mode repairs missing initial identities and depth entering the
    observed window. These repairs are counted; they do not recover true FIFO
    priority. Strict mode rejects unknown removals and unexplained depth changes.
    Hidden executions never consume displayed liquidity. Auctions rebuild the
    displayed state in reconciled mode; halt/resume messages leave orders intact.
    """
    required = {"time_seconds", "event_type", "order_id", "event_size", "event_price", "direction"}
    level_columns = []
    level = 1
    while True:
        suffix = "" if level == 1 else f"_{level}"
        columns = [f"{side}_{value}{suffix}" for side in ("ask", "bid") for value in ("price", "size")]
        if not any(column in events.columns for column in columns):
            break
        if not all(column in events.columns for column in columns):
            raise ValueError(f"Incomplete depth level {level}")
        level_columns.append(columns)
        required.update(columns)
        level += 1
    missing = required.difference(events.columns)
    if missing or not level_columns:
        raise ValueError(f"Missing replay columns: {sorted(missing) if missing else 'book depth'}")
    if events.empty:
        raise ValueError("No events to replay")
    if not events.columns.is_unique:
        raise ValueError("Replay columns must be unique")
    engine = MatchingEngine()
    summary = ReplaySummary()
    # Synthetic IDs cannot collide with LOBSTER's positive order IDs.
    next_id = -1
    locations: dict[int, tuple[str, int]] = {}
    queues: dict[tuple[str, int], dict[int, None]] = {}
    historical: dict[int, int] = {}
    observed_ids: set[int] = set()
    used_historical_ids: set[int] = set()
    previous_time = -math.inf
    previous_expected = {}
    halted = False

    def integer(value, name):
        if isinstance(value, bool) or not math.isfinite(float(value)) or int(value) != value:
            raise ValueError(f"{name} must be a finite integer")
        return int(value)

    def note(message):
        if len(summary.discrepancies) < 20:
            summary.discrepancies.append(message)

    def add(side, price, quantity, order_id=None):
        nonlocal next_id
        if order_id is not None and order_id not in used_historical_ids:
            internal_id = order_id
            used_historical_ids.add(order_id)
        else:
            internal_id = next_id
            next_id -= 1
        engine.add_resting(internal_id, side, quantity, price)
        key = (side, price)
        locations[internal_id] = key
        queues.setdefault(key, {})[internal_id] = None
        if order_id is not None:
            historical[order_id] = internal_id
            observed_ids.add(internal_id)

    def remove(internal_id, quantity=None, execution=False):
        if execution:
            engine.execute_resting(internal_id, quantity)
        else:
            engine.cancel(internal_id, quantity)
        if engine.order(internal_id) is None:
            observed_ids.discard(internal_id)
            key = locations.pop(internal_id)
            queues[key].pop(internal_id)
            if not queues[key]:
                del queues[key]

    def infer_removal(side, price, quantity):
        remaining = quantity
        visible = (side, price) in queues
        # Identity is unknown. Prefer anonymous liquidity; report this assumption.
        ids = sorted(queues.get((side, price), {}), key=lambda ident: ident in observed_ids)
        for ident in ids:
            amount = min(remaining, engine.order(ident).quantity)
            remove(ident, amount)
            summary.inferred_removal_quantity += amount
            remaining -= amount
            if not remaining:
                break
        if remaining and visible:
            summary.unexplained_removal_quantity += remaining
            note(f"{context}: reported removal exceeds available visible liquidity by {remaining}")

    for row_number, values in enumerate(events.itertuples(index=False, name=None)):
        row = dict(zip(events.columns, values))
        timestamp = float(row["time_seconds"])
        if not math.isfinite(timestamp) or timestamp < 0 or timestamp < previous_time:
            raise ValueError(f"Row {row_number}: times must be finite and nondecreasing")
        previous_time = timestamp
        event_type = integer(row["event_type"], "event_type")
        if event_type not in range(1, 8):
            raise ValueError(f"Row {row_number}: unsupported event type {event_type}")
        order_id = integer(row["order_id"], "order_id")
        quantity = integer(row["event_size"], "event_size")
        price = integer(row["event_price"], "event_price")
        direction = integer(row["direction"], "direction")
        context = f"Row {row_number}, time {timestamp}, event {event_type}, order {order_id}"
        if quantity < 0 or order_id < 0:
            raise ValueError(f"{context}: negative message size or order ID")
        if event_type in (1, 2, 3, 4) and (
            direction not in (-1, 1) or quantity <= 0 or price <= 0 or order_id <= 0
        ):
            raise ValueError(f"{context}: invalid visible order message")
        if event_type == 7 and price not in (-1, 0, 1):
            raise ValueError(f"{context}: unsupported trading status {price}")
        expected = {}
        prior_prices = {}
        empty_sides = set()
        for ask_price, ask_size, bid_price, bid_size in level_columns:
            for side, price_column, size_column in (("sell", ask_price, ask_size), ("buy", bid_price, bid_size)):
                p = integer(row[price_column], price_column)
                q = integer(row[size_column], size_column)
                if q < 0:
                    raise ValueError(f"{context}: negative depth")
                if q == 0:
                    empty_sides.add(side)
                    continue  # LOBSTER uses sentinel prices for absent levels.
                if p <= 0 or abs(p) >= 9_999_999_999:
                    raise ValueError(f"{context}: invalid populated depth price {p}")
                if (side, p) in expected:
                    raise ValueError(f"{context}: repeated depth price {p}")
                if side in empty_sides or (side in prior_prices and (
                    (side == "sell" and p <= prior_prices[side])
                    or (side == "buy" and p >= prior_prices[side])
                )):
                    raise ValueError(f"{context}: depth levels must be ordered and contiguous")
                prior_prices[side] = p
                expected[side, p] = q
        if row_number == 0:
            for (side, p), q in expected.items():
                add(side, p, q)
            summary.seeded_rows = 1
            halted = event_type == 7 and price in (-1, 0)
        elif event_type == 5:
            summary.hidden_executions += 1
        elif event_type == 6:
            summary.auctions += 1
            if strict:
                raise ReplayError(f"{context}: auction cannot be reconstructed from continuous-book messages")
            for internal_id in list(locations):
                remove(internal_id)
        elif event_type == 7:
            if price == -1:
                halted = True
                summary.halts += 1
            elif price == 0:
                summary.quoting_resume_events += 1
            elif price == 1:
                halted = False
                summary.resume_events += 1
            else:
                raise ValueError(f"{context}: unsupported trading status {price}")
        else:
            if direction not in (-1, 1) or quantity <= 0 or price <= 0 or order_id <= 0:
                raise ValueError(f"{context}: invalid visible order message")
            side = "buy" if direction == 1 else "sell"
            internal_id = historical.get(order_id)
            known = engine.order(internal_id) if internal_id is not None else None
            if halted and event_type == 4 and strict:
                raise ReplayError(f"{context}: visible execution while trading is halted")
            if event_type == 1:
                if order_id in historical:
                    raise ReplayError(f"{context}: duplicate submitted order ID")
                add(side, price, quantity, order_id)
                summary.applied_events += 1
            elif known is None:
                summary.unknown_order_events += 1
                note(f"{context}: order identity unavailable")
                if strict:
                    raise ReplayError(f"{context}: unknown order ID (initial or outside observed depth)")
                infer_removal(side, price, quantity)
            elif (known.side != side or known.price != price or quantity > known.quantity
                  or (event_type == 3 and quantity != known.quantity)):
                summary.conflicting_order_events += 1
                note(f"{context}: message conflicts with known resting order")
                if strict:
                    raise ReplayError(f"{context}: message conflicts with known resting order")
                infer_removal(side, price, quantity)
            else:
                remove(internal_id, None if event_type == 3 else quantity, event_type == 4)
                summary.applied_events += 1

        actual = {}
        snapshot = engine.snapshot(depth=len(level_columns))
        for side, key in (("buy", "bids"), ("sell", "asks")):
            actual.update({(side, p): q for p, q in snapshot[key]})
        if actual != expected:
            if strict:
                raise ReplayError(f"{context}: snapshot mismatch; expected {expected}, got {actual}")
            # New outer levels are supplied by the finite-depth snapshot. Audit
            # common prices and the observable window, rather than calling a
            # newly exposed deeper level an unexplained event discrepancy.
            unexplained = event_type in (5, 7) or any(
                actual[key] != expected[key] for key in actual.keys() & expected.keys()
            )
            for side, p in actual.keys() - expected.keys():
                prices = [price for s, price in expected if s == side]
                if not prices or (side == "sell" and p <= max(prices)) or (side == "buy" and p >= min(prices)):
                    unexplained = True
            for side, p in expected.keys() - actual.keys():
                prices = [price for s, price in previous_expected if s == side]
                if len(prices) < len(level_columns) or (prices and (
                    (side == "sell" and p <= max(prices)) or (side == "buy" and p >= min(prices))
                )):
                    unexplained = True
            if unexplained and event_type != 6:
                summary.snapshot_mismatches += 1
                note(f"{context}: displayed depth differs from replay")
        if not strict:
            # Window changes are expected. Keep them separate from top-depth mismatches.
            full = engine.snapshot()
            actual = {(side, p): q for side, name in (("buy", "bids"), ("sell", "asks"))
                      for p, q in full[name]}
            for key in sorted(set(actual) | set(expected)):
                current, target = actual.get(key, 0), expected.get(key, 0)
                if current == target:
                    continue
                summary.reconciliations += 1
                if target == 0:
                    summary.depth_exits += 1
                elif current == 0:
                    summary.depth_entries += 1
                if current > target:
                    remaining = current - target
                    # Reduce unknown liquidity first, then invalidate observed identities.
                    ids = list(queues[key])
                    ids.sort(key=lambda ident: ident in observed_ids)
                    for ident in ids:
                        size = min(remaining, engine.order(ident).quantity)
                        remove(ident, size)
                        remaining -= size
                        if not remaining:
                            break
                else:
                    add(*key, target - current)
            verified = engine.snapshot()
            reconstructed = {(side, p): q for side, name in (("buy", "bids"), ("sell", "asks")) for p, q in verified[name]}
            if reconstructed != expected:
                raise ReplayError(f"{context}: reconciliation failed")
        summary.rows += 1
        previous_expected = expected
    return ReplayResult(engine, summary)
