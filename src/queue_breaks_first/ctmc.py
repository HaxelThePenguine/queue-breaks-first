"""A finite two-queue continuous-time Markov model: exercises for the learner."""

from __future__ import annotations


def build_generator(max_queue: int, birth_bid: float, death_bid: float, birth_ask: float, death_ask: float):
    """Construct the transient-state generator and boundary transition rates.

    TODO: states are (q_bid, q_ask) with 1 <= each queue <= max_queue.
    A birth adds one unit, a death removes one unit. Choose and document a
    boundary rule at max_queue. At q_ask=0 the next move is up; at q_bid=0
    the next move is down. Return objects needed by up_move_probability().
    """
    raise NotImplementedError("Exercise 4 in LEARNING_PATH.md")


def up_move_probability(q_bid: int, q_ask: int, *, max_queue: int, birth_bid: float, death_bid: float, birth_ask: float, death_ask: float) -> float:
    """Solve L h = 0 with h(q_bid, 0)=1 and h(0, q_ask)=0.

    TODO: use scipy.sparse and scipy.sparse.linalg. Check the input domain.
    For q_bid=q_ask and equal bid/ask rates, the answer should be 0.5.
    """
    raise NotImplementedError("Exercise 4 in LEARNING_PATH.md")
