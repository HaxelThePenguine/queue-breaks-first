"""Load aligned LOBSTER-shaped files and sample price-move observations."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

MESSAGE_COLUMNS = ["time_seconds", "event_type", "order_id", "event_size", "event_price", "direction"]
TOP_OF_BOOK_COLUMNS = ["ask_price", "ask_size", "bid_price", "bid_size"]


def _read_pair(message_file, orderbook_file, *, levels: int | None = 1) -> pd.DataFrame:
    if levels is not None and (isinstance(levels, bool) or not isinstance(levels, int) or levels < 1):
        raise ValueError("levels must be a positive integer or None")
    message_types = {name: "int64" for name in MESSAGE_COLUMNS[1:]}
    message_types["time_seconds"] = "float64"
    messages = pd.read_csv(message_file, header=None, names=MESSAGE_COLUMNS,
                           usecols=range(6), dtype=message_types)
    book = pd.read_csv(orderbook_file, header=None, dtype="int64")
    if book.shape[1] < 4 or book.shape[1] % 4:
        raise ValueError("Each book level requires four columns")
    available = book.shape[1] // 4
    if levels is not None and levels > available:
        raise ValueError(f"Requested {levels} levels, input has {available}")
    count = available if levels is None else levels
    book = book.iloc[:, :4 * count].copy()
    book.columns = [name if level == 1 else f"{name}_{level}"
                    for level in range(1, count + 1) for name in TOP_OF_BOOK_COLUMNS]
    if len(messages) != len(book):
        raise ValueError(f"Message/book row counts differ: {len(messages)} vs {len(book)}")
    if messages.empty:
        raise ValueError("The input files contain no book updates")
    result = pd.concat([messages.reset_index(drop=True), book.reset_index(drop=True)], axis=1)
    numeric = ["time_seconds", *book.columns]
    if result[numeric].isna().any().any():
        raise ValueError("Missing numeric fields in the top-of-book data")
    if (result["time_seconds"].diff().dropna() < 0).any():
        raise ValueError("Message times must be nondecreasing")
    if not np.isfinite(result["time_seconds"]).all() or (result["time_seconds"] < 0).any():
        raise ValueError("Message times must be finite and nonnegative")
    if not result["event_type"].between(1, 7).all():
        raise ValueError("Unsupported LOBSTER event type")
    if (result["event_size"] < 0).any():
        raise ValueError("Event sizes must be nonnegative")
    if not result["direction"].isin([-1, 1]).all():
        raise ValueError("LOBSTER direction must be -1 or 1")
    if (result.filter(regex=r"^(bid|ask)_size(_\d+)?$") < 0).any().any():
        raise ValueError("Book sizes must be nonnegative")
    return result


def load_lobster_pair(message_path: str | Path, orderbook_path: str | Path,
                      *, levels: int | None = 1) -> pd.DataFrame:
    """Load aligned CSVs. Set levels=None to retain the full supplied depth."""
    return _read_pair(message_path, orderbook_path, levels=levels)


def load_lobster_zip(zip_path: str | Path, *, levels: int | None = 1) -> pd.DataFrame:
    """Load the message and orderbook CSVs directly from an official sample ZIP."""
    with ZipFile(zip_path) as archive:
        message_names = [name for name in archive.namelist() if "_message_" in name and name.endswith(".csv")]
        book_names = [name for name in archive.namelist() if "_orderbook_" in name and name.endswith(".csv")]
        if len(message_names) != 1 or len(book_names) != 1:
            raise ValueError("Expected exactly one message CSV and one orderbook CSV in the ZIP")
        with archive.open(message_names[0]) as message_file, archive.open(book_names[0]) as book_file:
            return _read_pair(message_file, book_file, levels=levels)


def sample_price_spells(events: pd.DataFrame, *, tick_size_scaled: int | None = 100) -> pd.DataFrame:
    """Take the first book state of each mid-price spell and label its next move.

    LOBSTER prices are integer dollars × 10,000. A $0.01 tick is therefore 100.
    Set ``tick_size_scaled=None`` to keep all positive-spread observations.
    """
    required = {"time_seconds", "ask_price", "ask_size", "bid_price", "bid_size"}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if tick_size_scaled is not None and tick_size_scaled <= 0:
        raise ValueError("tick_size_scaled must be positive")

    twice_mid = (events["ask_price"] + events["bid_price"]).to_numpy()
    starts = np.flatnonzero(np.r_[True, twice_mid[1:] != twice_mid[:-1]])
    columns = ["time_seconds", "bid_price", "ask_price", "bid_size", "ask_size"]
    if len(starts) < 2:
        return pd.DataFrame(columns=columns + ["spread_scaled", "next_move_up"])

    observations = events.iloc[starts[:-1]][columns].copy().reset_index(drop=True)
    observations["spread_scaled"] = observations["ask_price"] - observations["bid_price"]
    observations["next_move_up"] = (twice_mid[starts[1:]] > twice_mid[starts[:-1]]).astype(int)
    valid = (
        (observations["spread_scaled"] > 0)
        & (observations["bid_size"] > 0)
        & (observations["ask_size"] > 0)
    )
    if tick_size_scaled is not None:
        valid &= observations["spread_scaled"] == tick_size_scaled
    return observations.loc[valid].reset_index(drop=True)
