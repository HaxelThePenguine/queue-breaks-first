from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from queue_breaks_first.data import load_lobster_pair, load_lobster_zip, sample_price_spells


def test_pair_and_zip_load_the_same_rows(tmp_path: Path):
    messages = "1,1,1,100,1000100,-1\n2,4,2,100,1000100,-1\n3,1,3,100,1000200,-1\n"
    book = "1000100,200,1000000,400\n1000100,100,1000000,400\n1000200,300,1000100,400\n"
    message_path = tmp_path / "sample_message_1.csv"
    book_path = tmp_path / "sample_orderbook_1.csv"
    message_path.write_text(messages)
    book_path.write_text(book)
    expected = load_lobster_pair(message_path, book_path)
    with ZipFile(tmp_path / "sample.zip", "w") as archive:
        archive.write(message_path, message_path.name)
        archive.write(book_path, book_path.name)
    actual = load_lobster_zip(tmp_path / "sample.zip")
    pd.testing.assert_frame_equal(actual, expected)


def test_price_spells_take_one_state_per_mid_price_run():
    events = pd.DataFrame({
        "time_seconds": [1, 2, 3, 4, 5],
        "ask_price": [1100, 1100, 1200, 1200, 1100],
        "bid_price": [1000, 1000, 1100, 1100, 1000],
        "ask_size": [10, 8, 12, 11, 10],
        "bid_size": [20, 22, 9, 8, 20],
    })
    result = sample_price_spells(events)
    assert result["time_seconds"].tolist() == [1, 3]
    assert result["next_move_up"].tolist() == [1, 0]


def test_mismatched_row_counts_fail(tmp_path: Path):
    message_path = tmp_path / "message.csv"
    book_path = tmp_path / "book.csv"
    message_path.write_text("1,1,1,100,1100,-1\n2,1,2,100,1100,-1\n")
    book_path.write_text("1100,10,1000,10\n")
    with pytest.raises(ValueError, match="row counts differ"):
        load_lobster_pair(message_path, book_path)
