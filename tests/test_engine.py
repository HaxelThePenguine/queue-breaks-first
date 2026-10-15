from dataclasses import FrozenInstanceError
import random

import pytest

from queue_breaks_first.engine import MatchingEngine


def test_price_time_priority_and_partial_fills():
    book = MatchingEngine()
    book.submit(1, "sell", 4, 102)
    book.submit(2, "sell", 5, 101)
    book.submit(3, "sell", 7, 101)
    result = book.submit(4, "buy", 14, 103)
    assert [(t.maker_order_id, t.price, t.quantity) for t in result.fills] == [
        (2, 101, 5), (3, 101, 7), (1, 102, 2)
    ]
    assert result.filled_quantity == 14
    assert result.remaining_quantity == result.resting_quantity == result.cancelled_quantity == 0
    assert book.snapshot() == {"bids": (), "asks": ((102, 2),)}
    assert book.order(1).quantity == 2
    assert book.order(2) is None


def test_limit_remainder_and_market_ioc():
    book = MatchingEngine()
    book.submit(1, "sell", 2, 100)
    book.submit(2, "sell", 3, 102)
    result = book.submit(3, "buy", 5, 101)
    assert (result.filled_quantity, result.resting_quantity, result.cancelled_quantity) == (2, 3, 0)
    assert book.snapshot() == {"bids": ((101, 3),), "asks": ((102, 3),)}
    result = book.submit(4, "buy", 8)
    assert (result.filled_quantity, result.remaining_quantity, result.cancelled_quantity) == (3, 5, 5)
    assert result.resting_quantity == 0
    assert book.order(4) is None


def test_ioc_limit_and_fok_atomicity():
    book = MatchingEngine()
    book.submit(1, "buy", 4, 101)
    book.submit(2, "buy", 8, 99)
    before = book.snapshot()
    rejected = book.submit(3, "sell", 5, 100, time_in_force="FOK")
    assert rejected.fills == ()
    assert rejected.cancelled_quantity == 5
    assert book.snapshot() == before
    filled = book.submit(4, "sell", 10, 99, time_in_force="FOK")
    assert [(t.price, t.quantity) for t in filled.fills] == [(101, 4), (99, 6)]
    assert filled.filled_quantity == 10
    result = book.submit(5, "sell", 5, 99, time_in_force="IOC")
    assert (result.filled_quantity, result.cancelled_quantity) == (2, 3)
    assert book.snapshot() == {"bids": (), "asks": ()}


def test_post_only_rejection_does_not_consume_id_or_change_book():
    book = MatchingEngine()
    book.submit(1, "sell", 3, 100)
    with pytest.raises(ValueError, match="post-only"):
        book.submit(2, "buy", 1, 100, time_in_force="POST_ONLY")
    assert book.order(1).quantity == 3
    result = book.submit(2, "buy", 1, 99, time_in_force="post_only")
    assert result.resting_quantity == 1


def test_reduce_preserves_fifo_increase_loses_fifo():
    book = MatchingEngine()
    book.submit(1, "sell", 5, 100)
    book.submit(2, "sell", 5, 100)
    book.replace(1, 3)
    book.replace(1, 3)
    result = book.submit(3, "buy", 1)
    assert result.fills[0].maker_order_id == 1
    book.replace(1, 4)
    result = book.submit(4, "buy", 6)
    assert [(t.maker_order_id, t.quantity) for t in result.fills] == [(2, 5), (1, 1)]


def test_reprice_matches_and_then_rests():
    book = MatchingEngine()
    book.submit(1, "buy", 5, 99)
    book.submit(2, "sell", 2, 101)
    result = book.replace(1, 5, 102)
    assert [(t.maker_order_id, t.taker_order_id, t.price, t.quantity) for t in result.fills] == [(2, 1, 101, 2)]
    assert book.snapshot() == {"bids": ((102, 3),), "asks": ()}


def test_targeted_historical_execution_and_cancel_atomicity():
    book = MatchingEngine()
    book.seed(-1, "sell", 3, 100)
    book.add_resting(1, "sell", 5, 100)
    book.add_resting(2, "buy", 1, 101)  # Reconstruction can contain crossed snapshots.
    book.execute_resting(1, 2)
    assert book.order(-1).quantity == 3
    assert book.order(1).quantity == 3
    before = book.snapshot()
    with pytest.raises(ValueError):
        book.cancel(1, 4)
    assert book.snapshot() == before
    assert book.cancel(1) == 3
    assert book.cancel(2) == 1
    assert book.snapshot(1) == {"bids": (), "asks": ((100, 3),)}
    with pytest.raises(KeyError):
        book.execute_resting(1, 1)
    with pytest.raises(ValueError, match="already"):
        book.submit(1, "buy", 1, 99)


@pytest.mark.parametrize("field,value", [
    ("order_id", True), ("order_id", 1.0), ("quantity", True),
    ("quantity", 2.0), ("quantity", 0), ("quantity", -1),
    ("price", True), ("price", 99.5), ("price", 0), ("side", "bid"),
    ("time_in_force", "DAY"), ("time_in_force", None),
])
def test_invalid_submission_is_atomic(field, value):
    book = MatchingEngine()
    book.submit(1, "sell", 2, 100)
    args = dict(order_id=2, side="buy", quantity=1, price=101, time_in_force="GTC")
    args[field] = value
    with pytest.raises((ValueError, TypeError)):
        book.submit(**args)
    assert book.snapshot() == {"bids": (), "asks": ((100, 2),)}
    assert book.order(1).quantity == 2


@pytest.mark.parametrize("order_id", [-7, 0])
def test_signed_and_zero_ids_support_the_order_lifecycle(order_id):
    book = MatchingEngine()
    book.submit(order_id, "sell", 4, 100)
    assert book.order(order_id).quantity == 4
    book.replace(order_id, 3)
    assert book.cancel(order_id, 1) == 1
    assert book.order(order_id).quantity == 2
    assert book.execute_resting(order_id, 2) == 2
    assert book.order(order_id) is None
    assert book.snapshot() == {"bids": (), "asks": ()}


def test_read_views_are_immutable_and_depth_is_validated():
    book = MatchingEngine()
    book.submit(1, "buy", 1, 100)
    book.submit(2, "buy", 1, 99)
    saved = book.order(1)
    with pytest.raises(FrozenInstanceError):
        saved.quantity = 8
    snapshot = book.snapshot()
    snapshot["bids"] = ()
    assert book.snapshot(1)["bids"] == ((100, 1),)
    assert book.snapshot(0)["bids"] == ()
    for depth in (-1, True, 1.5):
        with pytest.raises((ValueError, TypeError)):
            book.snapshot(depth)


@pytest.mark.parametrize("operation", [
    lambda book: book.cancel(1, 0),
    lambda book: book.cancel(1, True),
    lambda book: book.cancel(1, 2.5),
    lambda book: book.execute_resting(1, 0),
    lambda book: book.replace(1, 0),
    lambda book: book.replace(1, 3, 0),
    lambda book: book.replace(1, 3, 99.5),
    lambda book: book.add_resting(2, "buy", 2, None),
])
def test_invalid_book_mutations_leave_order_and_priority_unchanged(operation):
    book = MatchingEngine()
    book.submit(1, "sell", 2, 100)
    book.submit(3, "sell", 2, 100)
    with pytest.raises((ValueError, TypeError)):
        operation(book)
    assert book.snapshot()["asks"] == ((100, 4),)
    assert book.order(1).quantity == 2
    assert book.submit(4, "buy", 1).fills[0].maker_order_id == 1


@pytest.mark.parametrize("seed", [0, 7, 42])
def test_randomized_matching_against_list_reference(seed):
    """Independent slow list book checks fills, FIFO and volume conservation."""
    rng = random.Random(seed)
    book = MatchingEngine()
    resting = []  # [id, side, quantity, price, priority]
    accepted = executed = cancelled = 0
    sequence = 0
    for order_id in range(1, 401):
        if resting and rng.random() < .25:
            old = rng.choice(resting)
            removed = rng.randint(1, old[2])
            book.cancel(old[0], removed)
            old[2] -= removed
            cancelled += removed
            resting = [item for item in resting if item[2]]
        if resting and rng.random() < .2:
            old = rng.choice(resting)
            previous = old[2]
            replacement = rng.randint(1, 25)
            book.replace(old[0], replacement)
            if replacement > previous:
                sequence += 1
                old[4] = sequence
                accepted += replacement - previous
            else:
                cancelled += previous - replacement
            old[2] = replacement
        side = rng.choice(["buy", "sell"])
        quantity = rng.randint(1, 25)
        price = None if rng.random() < .2 else rng.randint(97, 103)
        tif = rng.choice(["GTC", "IOC", "FOK"]) if price else "IOC"
        opposite = [item for item in resting if item[1] != side and (
            price is None or (item[3] <= price if side == "buy" else item[3] >= price)
        )]
        opposite.sort(key=lambda item: (item[3] if side == "buy" else -item[3], item[4]))
        expected = []
        remaining = quantity
        if tif != "FOK" or sum(item[2] for item in opposite) >= quantity:
            for maker in opposite:
                taken = min(remaining, maker[2])
                expected.append((maker[0], order_id, maker[3], taken, maker[1]))
                maker[2] -= taken
                remaining -= taken
                if not remaining:
                    break
        resting = [item for item in resting if item[2]]
        rest = remaining if price and tif == "GTC" else 0
        sequence += 1
        if rest:
            resting.append([order_id, side, rest, price, sequence])
        result = book.submit(order_id, side, quantity, price, time_in_force=tif)
        actual = [(t.maker_order_id, t.taker_order_id, t.price, t.quantity, t.maker_side) for t in result.fills]
        assert actual == expected
        assert result.filled_quantity + result.remaining_quantity == quantity
        assert result.resting_quantity + result.cancelled_quantity == remaining
        accepted += quantity
        executed += quantity - remaining
        cancelled += remaining - rest
        # Each trade removes one maker unit and one incoming unit.
        assert accepted == 2 * executed + cancelled + sum(item[2] for item in resting)
        expected_snapshot = {}
        for key, book_side in [("bids", "buy"), ("asks", "sell")]:
            levels = {}
            for item in resting:
                if item[1] == book_side:
                    levels[item[3]] = levels.get(item[3], 0) + item[2]
            expected_snapshot[key] = tuple(sorted(levels.items(), reverse=book_side == "buy"))
        assert book.snapshot() == expected_snapshot
        for item in resting:
            assert book.order(item[0]).quantity == item[2]
