import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_script(name, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
                          cwd=ROOT, env=env, text=True, capture_output=True)


def test_matching_demo(tmp_path):
    output = tmp_path / "matching.json"
    result = run_script("match_orders.py", "--output", output)
    assert result.returncode == 0, result.stderr
    summary = json.loads(output.read_text())
    assert [trade["maker_order_id"] for trade in summary["trades"]] == [1, 2, 3]
    assert [trade["quantity"] for trade in summary["trades"]] == [100, 60, 50]
    assert summary["filled_quantity"] == 210
    assert summary["book"] == {"bids": [[1000000, 200]], "asks": [[1000200, 100]]}


def test_matching_csv_replace_and_ioc(tmp_path):
    commands = tmp_path / "commands.csv"
    commands.write_text(
        "action,order_id,side,quantity,price,time_in_force\n"
        "submit,1,sell,100,101,GTC\n"
        "submit,2,sell,100,101,GTC\n"
        "replace,1,,120,,\n"
        "cancel,2,,25,,\n"
        "submit,3,buy,200,101,IOC\n"
    )
    output = tmp_path / "matching.json"
    result = run_script("match_orders.py", "--input", commands, "--output", output)
    assert result.returncode == 0, result.stderr
    summary = json.loads(output.read_text())
    assert [trade["maker_order_id"] for trade in summary["trades"]] == [2, 1]
    assert [trade["quantity"] for trade in summary["trades"]] == [75, 120]
    assert summary["results"][-1]["cancelled_quantity"] == 5
    assert summary["book"] == {"bids": [], "asks": []}


def test_matching_invalid_command_does_not_write_report(tmp_path):
    commands = tmp_path / "commands.csv"
    commands.write_text("action,order_id,quantity\ncancel,123,5\n")
    output = tmp_path / "matching.json"
    result = run_script("match_orders.py", "--input", commands, "--output", output)
    assert result.returncode != 0
    assert "Command 1:" in result.stderr
    assert not output.exists()


def test_replay_demo_strict(tmp_path):
    output = tmp_path / "replay.json"
    result = run_script("replay_book.py", "--strict", "--output", output)
    assert result.returncode == 0, result.stderr
    summary = json.loads(output.read_text())
    assert summary["rows"] == 97
    assert summary["applied_events"] == 96
    assert summary["seeded_rows"] == 1
    assert summary["unknown_order_events"] == summary["reconciliations"] == 0
    assert summary["snapshot_mismatches"] == 0


def test_replay_custom_pair_and_corrupted_snapshot(tmp_path):
    message = ROOT / "data" / "demo" / "demo_message.csv"
    original = ROOT / "data" / "demo" / "demo_orderbook.csv"
    output = tmp_path / "replay.json"
    result = run_script("replay_book.py", "--message", message, "--orderbook", original,
                        "--strict", "--levels", "1", "--output", output)
    assert result.returncode == 0, result.stderr
    rows = list(csv.reader(original.open()))
    rows[1][1] = str(int(rows[1][1]) + 1)
    corrupted = tmp_path / "orderbook.csv"
    with corrupted.open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)
    result = run_script("replay_book.py", "--message", message, "--orderbook", corrupted,
                        "--strict", "--output", tmp_path / "bad.json")
    assert result.returncode != 0
    assert "snapshot mismatch" in result.stderr
    assert not (tmp_path / "bad.json").exists()


def test_replay_requires_both_paths(tmp_path):
    result = run_script("replay_book.py", "--message", tmp_path / "message.csv")
    assert result.returncode != 0
    assert "must be supplied together" in result.stderr
