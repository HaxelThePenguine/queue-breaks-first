import pandas as pd
import pytest

from queue_breaks_first.replay import ReplayError, replay_lobster


def frame(messages, books):
    columns = ["time_seconds", "event_type", "order_id", "event_size", "event_price", "direction"]
    levels = len(books[0]) // 4
    for level in range(1, levels + 1):
        suffix = "" if level == 1 else f"_{level}"
        columns.extend(f"{side}_{value}{suffix}" for side in ("ask", "bid") for value in ("price", "size"))
    return pd.DataFrame([message + book for message, book in zip(messages, books)], columns=columns)


def test_known_orders_partial_fill_cancel_delete_and_fifo():
    data = frame([
        [1, 1, 999, 5, 110, -1],
        [2, 1, 10, 4, 110, -1],
        [2, 1, 11, 3, 110, -1],
        [3, 4, 10, 2, 110, -1],
        [4, 2, 11, 1, 110, -1],
        [5, 3, 10, 2, 110, -1],
    ], [[110, q, 100, 8, 120, 7, 90, 6] for q in [5, 9, 12, 10, 9, 7]])
    result = replay_lobster(data, strict=True)
    assert result.summary.applied_events == 5
    assert result.summary.seeded_rows == 1
    assert result.summary.snapshot_mismatches == 0
    assert result.engine.order(10) is None
    assert result.engine.order(11).quantity == 2
    fills = result.engine.submit(1234, "buy", 7, 110).fills
    assert [(fill.maker_order_id, fill.quantity) for fill in fills] == [(-1, 5), (11, 2)]


def test_initial_identity_unknown_is_counted_and_strict_rejects():
    data = frame([[1, 1, 10, 5, 110, -1], [2, 4, 10, 2, 110, -1]],
                 [[110, 5, 100, 8], [110, 3, 100, 8]])
    result = replay_lobster(data)
    assert result.engine.snapshot()["asks"] == ((110, 3),)
    assert result.summary.unknown_order_events == 1
    assert result.summary.snapshot_mismatches == 0
    assert result.summary.reconciliations == 0
    assert result.summary.inferred_removal_quantity == 2
    with pytest.raises(ReplayError, match="Row 1.*unknown order"):
        replay_lobster(data, strict=True)


def test_price_window_entries_and_exits_are_explicit():
    data = frame([[1, 5, 0, 0, 110, -1], [2, 1, 10, 4, 105, -1], [3, 3, 10, 4, 105, -1]],
                 [[110, 5, 100, 8, 120, 7, 90, 6],
                  [105, 4, 100, 8, 110, 5, 90, 6],
                  [110, 5, 100, 8, 120, 9, 90, 6]])
    result = replay_lobster(data)
    assert result.summary.depth_exits == 1
    assert result.summary.depth_entries == 1
    assert result.summary.snapshot_mismatches == 0
    assert result.engine.snapshot()["asks"] == ((110, 5), (120, 9))


def test_strict_retains_previously_observed_depth_outside_window():
    data = frame([[1, 5, 0, 0, 110, -1], [2, 1, 10, 4, 105, -1], [3, 3, 10, 4, 105, -1]],
                 [[110, 5, 100, 8, 120, 7, 90, 6],
                  [105, 4, 100, 8, 110, 5, 90, 6],
                  [110, 5, 100, 8, 120, 7, 90, 6]])
    result = replay_lobster(data, strict=True)
    assert result.summary.reconciliations == 0
    assert result.engine.snapshot()["asks"] == ((110, 5), (120, 7))


def test_hidden_halt_resume_and_auction():
    data = frame([[1, 5, 0, 0, 110, -1], [2, 5, 44, 100, 110, -1],
                  [3, 7, 0, 0, -1, 0], [4, 7, 0, 0, 0, 0], [5, 6, 0, 0, 0, 0]],
                 [[110, 5, 100, 8]] * 4 + [[111, 9, 99, 7]])
    result = replay_lobster(data)
    assert result.summary.hidden_executions == 1
    assert result.summary.halts == 1
    assert result.summary.quoting_resume_events == 1
    assert result.summary.resume_events == 0
    assert result.summary.auctions == 1
    assert result.engine.snapshot() == {"bids": ((99, 7),), "asks": ((111, 9),)}
    with pytest.raises(ReplayError, match="auction"):
        replay_lobster(data, strict=True)


def test_bad_snapshot_fails_audit_and_is_repaired_by_default():
    data = frame([[1, 5, 0, 0, 110, -1], [2, 1, 22, 2, 110, -1]],
                 [[110, 5, 100, 8], [110, 10, 100, 8]])
    with pytest.raises(ReplayError, match="snapshot mismatch"):
        replay_lobster(data, strict=True)
    result = replay_lobster(data)
    assert result.summary.snapshot_mismatches == 1
    assert result.engine.snapshot()["asks"] == ((110, 10),)


def test_times_are_not_sorted_silently_and_missing_levels_are_empty():
    data = frame([[2, 5, 0, 0, 110, -1], [1, 5, 0, 0, 110, -1]],
                 [[110, 5, 100, 8, 9999999999, 0, -9999999999, 0]] * 2)
    with pytest.raises(ValueError, match="nondecreasing"):
        replay_lobster(data)
    assert replay_lobster(data.iloc[:1]).engine.snapshot()["asks"] == ((110, 5),)


@pytest.mark.parametrize("message", [
    [1, 1, 0, 5, 110, -1], [1, 1, 10, 0, 110, -1],
    [1, 1, 10, 5, -1, -1], [1, 1, 10, 5, 110, 0],
    [1, 7, 0, 0, 2, -1], [1, True, 10, 5, 110, -1],
])
def test_first_row_is_validated(message):
    with pytest.raises(ValueError):
        replay_lobster(frame([message], [[110, 5, 100, 8]]))


@pytest.mark.parametrize("book", [
    [120, 5, 100, 8, 110, 7, 90, 6],
    [110, 5, 90, 8, 120, 7, 100, 6],
    [9999999999, 0, 100, 8, 120, 7, 90, 6],
])
def test_malformed_depth_order_is_rejected(book):
    with pytest.raises(ValueError, match="ordered"):
        replay_lobster(frame([[1, 5, 0, 5, 110, -1]], [book]))


def test_delete_quantity_conflict_is_not_silently_accepted():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 1, 10, 4, 110, -1],
                  [3, 3, 10, 3, 110, -1]],
                 [[110, 5, 100, 8], [110, 9, 100, 8], [110, 6, 100, 8]])
    with pytest.raises(ReplayError, match="conflicts"):
        replay_lobster(data, strict=True)
    result = replay_lobster(data)
    assert result.summary.conflicting_order_events == 1


def test_quoting_resume_does_not_resume_executions():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 1, 10, 4, 110, -1],
                  [3, 7, 0, 0, -1, -1], [4, 7, 0, 0, 0, -1],
                  [5, 4, 10, 1, 110, -1]],
                 [[110, 5, 100, 8]] + [[110, 9, 100, 8]] * 3 + [[110, 8, 100, 8]])
    with pytest.raises(ReplayError, match="while trading is halted"):
        replay_lobster(data, strict=True)
    data.loc[3, "event_price"] = 1
    assert replay_lobster(data, strict=True).summary.resume_events == 1


def test_price_change_inside_prior_window_is_not_a_boundary_entry():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 5, 0, 5, 110, -1]],
                 [[110, 5, 100, 8, 130, 7, 90, 6],
                  [110, 5, 100, 8, 120, 7, 90, 6]])
    assert replay_lobster(data).summary.snapshot_mismatches == 1
    with pytest.raises(ReplayError, match="snapshot mismatch"):
        replay_lobster(data, strict=True)


def test_empty_observed_slot_does_not_hide_an_invented_level():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 5, 0, 5, 110, -1]],
                 [[110, 5, 100, 8, 9999999999, 0, -9999999999, 0],
                  [110, 5, 100, 8, 120, 7, -9999999999, 0]])
    assert replay_lobster(data).summary.snapshot_mismatches == 1


def test_unknown_removal_overflow_remains_visible_in_summary():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 4, 10, 100, 110, -1]],
                 [[110, 5, 100, 8], [120, 7, 100, 8]])
    result = replay_lobster(data)
    assert result.summary.inferred_removal_quantity == 5
    assert result.summary.unexplained_removal_quantity == 95


def test_initial_quoting_status_keeps_trading_halted():
    data = frame([[1, 7, 0, 0, 0, -1], [2, 1, 10, 4, 110, -1],
                  [3, 4, 10, 1, 110, -1]],
                 [[110, 5, 100, 8], [110, 9, 100, 8], [110, 8, 100, 8]])
    with pytest.raises(ReplayError, match="halted"):
        replay_lobster(data, strict=True)


def test_completed_historical_id_cannot_be_submitted_again():
    data = frame([[1, 5, 0, 5, 110, -1], [2, 1, 10, 4, 110, -1],
                  [3, 3, 10, 4, 110, -1], [4, 1, 10, 4, 110, -1]],
                 [[110, 5, 100, 8], [110, 9, 100, 8],
                  [110, 5, 100, 8], [110, 9, 100, 8]])
    with pytest.raises(ReplayError, match="duplicate submitted"):
        replay_lobster(data, strict=True)


@pytest.mark.parametrize("message", [[2, 5, 0, 5, 110, -1], [2, 7, 0, 0, -1, -1]])
def test_hidden_and_status_events_cannot_change_outer_depth(message):
    data = frame([[1, 5, 0, 5, 110, -1], message],
                 [[110, 5, 100, 8], [110, 5, 90, 7]])
    assert replay_lobster(data).summary.snapshot_mismatches == 1
