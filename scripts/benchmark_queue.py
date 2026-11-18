"""Measure market orders against a single long FIFO queue."""

from statistics import median
from time import perf_counter_ns

from queue_breaks_first.engine import MatchingEngine


QUEUE_SIZE = 100_000
MARKET_ORDERS = 100
RUNS = 5


def time_market_orders(queue_size):
    book = MatchingEngine()
    for order_id in range(queue_size):
        book.add_resting(order_id, "sell", 1, 100)

    start = perf_counter_ns()
    for order_id in range(queue_size, queue_size + MARKET_ORDERS):
        result = book.submit(order_id, "buy", 1)
        assert result.filled_quantity == 1
    elapsed_ns = perf_counter_ns() - start

    assert book.snapshot()["asks"] == ((100, queue_size - MARKET_ORDERS),)
    return elapsed_ns / MARKET_ORDERS / 1_000


def main():
    time_market_orders(1_000)  # Warm up before measuring.
    samples = [time_market_orders(QUEUE_SIZE) for _ in range(RUNS)]
    print(f"{median(samples):.3f} us/order ({QUEUE_SIZE:,} resting orders, {RUNS} runs)")


if __name__ == "__main__":
    main()
