"""Empirical models of best-quote queue imbalance."""

from __future__ import annotations


def queue_imbalance(bid_size, ask_size):
    """Return (bid_size - ask_size) / (bid_size + ask_size).

    Planned behavior: support scalars and NumPy arrays, reject negative queue
    sizes, and define the result when total displayed size is zero.
    """
    raise NotImplementedError("Queue imbalance model is pending implementation")
