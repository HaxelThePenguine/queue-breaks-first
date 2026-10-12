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


def test_depth_selection_and_integer_prices(tmp_path):
    message = tmp_path / "message.csv"
    book = tmp_path / "book.csv"
    message.write_text("1,1,1,10,1100,-1\n")
    book.write_text("1100,10,1000,20,1300,30,800,40\n")
    all_levels = load_lobster_pair(message, book, levels=None)
    assert all_levels["ask_price_2"].tolist() == [1300]
    assert all_levels["bid_size_2"].tolist() == [40]
    assert all_levels["ask_price_2"].dtype.kind == "i"
    assert "ask_price_2" not in load_lobster_pair(message, book)
    with pytest.raises(ValueError, match="input has 2"):
        load_lobster_pair(message, book, levels=3)


@pytest.mark.parametrize("levels", [0, -1, True, 1.5])
def test_invalid_depth(levels, tmp_path):
    with pytest.raises(ValueError, match="levels"):
        load_lobster_pair(tmp_path / "missing", tmp_path / "missing", levels=levels)


@pytest.mark.parametrize("row,match", [
    ("nan,1,1,10,1100,-1", "Missing numeric"),
    ("inf,1,1,10,1100,-1", "finite"),
    ("1,8,1,10,1100,-1", "event type"),
    ("1,1,1,-10,1100,-1", "sizes"),
    ("1,1,1,10,1100,0", "direction"),
])
def test_invalid_message_fields(row, match, tmp_path):
    message, book = tmp_path / "message.csv", tmp_path / "book.csv"
    message.write_text(row + "\n")
    book.write_text("1100,10,1000,20\n")
    with pytest.raises(ValueError, match=match):
        load_lobster_pair(message, book)


def test_zip_retains_all_levels(tmp_path):
    archive = tmp_path / "sample.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("sample_message_2.csv", "1,1,1,10,1100,-1\n")
        z.writestr("sample_orderbook_2.csv", "1100,10,1000,20,1200,30,900,40\n")
    events = load_lobster_zip(archive, levels=None)
    assert events["bid_price_2"].tolist() == [900]
