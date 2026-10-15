"""Integer-price FIFO book. Historical inserts deliberately skip matching."""

from collections import OrderedDict
from dataclasses import dataclass


def require_integer(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


@dataclass(frozen=True)
class Order:
    order_id: int
    side: str
    quantity: int
    price: int


@dataclass(frozen=True)
class Trade:
    maker_order_id: int
    taker_order_id: int
    price: int
    quantity: int
    maker_side: str


@dataclass(frozen=True)
class ExecutionResult:
    fills: tuple[Trade, ...]
    filled_quantity: int
    remaining_quantity: int
    resting_quantity: int
    cancelled_quantity: int


class MatchingEngine:
    """Single instrument, maker-price execution and unique lifetime order IDs.

    Prices and quantities are positive integers. Market orders are IOC; limit
    orders accept GTC, IOC, FOK and POST_ONLY. Remaining quantity is the unfilled
    quantity, split between resting and cancelled quantities. Replacements keep
    their ID, but increasing size or changing price loses FIFO priority.
    """

    def __init__(self):
        self._levels = {"buy": {}, "sell": {}}
        self._totals = {"buy": {}, "sell": {}}
        self._orders: dict[int, Order] = {}
        self._seen: set[int] = set()

    def _validate(self, order_id, side, quantity, price):
        require_integer(order_id, "order_id")
        if side not in ("buy", "sell"):
            raise ValueError("side must be buy or sell")
        require_integer(quantity, "quantity", minimum=1)
        if price is not None:
            require_integer(price, "price", minimum=1)

    def _prices(self, side):
        return sorted(self._levels[side], reverse=side == "buy")

    def _eligible(self, side, price):
        opposite = "sell" if side == "buy" else "buy"
        for maker_price in self._prices(opposite):
            if price is not None and (
                (side == "buy" and maker_price > price)
                or (side == "sell" and maker_price < price)
            ):
                break
            yield opposite, maker_price

    def _rest(self, order_id, side, quantity, price):
        order = Order(order_id, side, quantity, price)
        self._orders[order_id] = order
        self._levels[side].setdefault(price, OrderedDict())[order_id] = quantity
        self._totals[side][price] = self._totals[side].get(price, 0) + quantity

    def _reduce(self, order, quantity):
        level = self._levels[order.side][order.price]
        self._totals[order.side][order.price] -= quantity
        remaining = order.quantity - quantity
        if remaining:
            level[order.order_id] = remaining
            self._orders[order.order_id] = Order(
                order.order_id, order.side, remaining, order.price
            )
        else:
            del level[order.order_id]
            del self._orders[order.order_id]
            if not level:
                del self._levels[order.side][order.price]
                del self._totals[order.side][order.price]

    def _submit(self, order_id, side, quantity, price, tif):
        eligible = list(self._eligible(side, price))
        if tif == "POST_ONLY" and eligible:
            raise ValueError("post-only order would cross")
        self._seen.add(order_id)
        if tif == "FOK":
            available = sum(
                self._totals[maker_side][maker_price]
                for maker_side, maker_price in eligible
            )
            if available < quantity:
                return ExecutionResult((), 0, quantity, 0, quantity)
        remaining = quantity
        fills = []
        for maker_side, maker_price in eligible:
            for maker_id in list(self._levels[maker_side][maker_price]):
                maker = self._orders[maker_id]
                taken = min(remaining, maker.quantity)
                fills.append(Trade(maker_id, order_id, maker_price, taken, maker_side))
                self._reduce(maker, taken)
                remaining -= taken
                if not remaining:
                    break
            if not remaining:
                break
        resting = remaining if price is not None and tif in ("GTC", "POST_ONLY") else 0
        if resting:
            self._rest(order_id, side, resting, price)
        return ExecutionResult(
            tuple(fills), quantity - remaining, remaining, resting, remaining - resting
        )

    def submit(self, order_id: int, side: str, quantity: int, price: int | None = None,
               *, time_in_force: str = "GTC") -> ExecutionResult:
        self._validate(order_id, side, quantity, price)
        if order_id in self._seen:
            raise ValueError("order_id has already been used")
        if not isinstance(time_in_force, str):
            raise TypeError("time_in_force must be a string")
        tif = time_in_force.upper()
        if tif not in ("GTC", "IOC", "FOK", "POST_ONLY"):
            raise ValueError("unsupported time_in_force")
        if price is None:
            if tif in ("FOK", "POST_ONLY"):
                raise ValueError("market orders support IOC only")
            tif = "IOC"
        return self._submit(order_id, side, quantity, price, tif)

    def add_resting(self, order_id: int, side: str, quantity: int, price: int) -> Order:
        """Insert without crossing checks, for reconstructing historical books."""
        self._validate(order_id, side, quantity, price)
        if price is None:
            raise ValueError("resting order requires a price")
        if order_id in self._seen:
            raise ValueError("order_id has already been used")
        self._seen.add(order_id)
        self._rest(order_id, side, quantity, price)
        return self._orders[order_id]

    seed = add_resting

    def order(self, order_id: int) -> Order | None:
        require_integer(order_id, "order_id")
        return self._orders.get(order_id)

    def cancel(self, order_id: int, quantity: int | None = None) -> int:
        require_integer(order_id, "order_id")
        if quantity is not None:
            require_integer(quantity, "quantity", minimum=1)
        if order_id not in self._orders:
            raise KeyError(order_id)
        order = self._orders[order_id]
        removed = order.quantity if quantity is None else quantity
        if removed > order.quantity:
            raise ValueError("quantity exceeds resting order")
        self._reduce(order, removed)
        return removed

    def execute_resting(self, order_id: int, quantity: int) -> int:
        """Apply a reported execution to its exact historical maker order."""
        require_integer(quantity, "quantity", minimum=1)
        return self.cancel(order_id, quantity)

    def replace(self, order_id: int, quantity: int, price: int | None = None) -> ExecutionResult:
        require_integer(order_id, "order_id")
        require_integer(quantity, "quantity", minimum=1)
        if price is not None:
            require_integer(price, "price", minimum=1)
        if order_id not in self._orders:
            raise KeyError(order_id)
        old = self._orders[order_id]
        new_price = old.price if price is None else price
        if new_price == old.price and quantity <= old.quantity:
            self._reduce(old, old.quantity - quantity)
            return ExecutionResult((), 0, quantity, quantity, 0)
        self._reduce(old, old.quantity)
        return self._submit(order_id, old.side, quantity, new_price, "GTC")

    def snapshot(self, depth: int | None = None) -> dict:
        if depth is not None:
            require_integer(depth, "depth", minimum=0)
        return {
            name: tuple(
                (price, self._totals[side][price])
                for price in self._prices(side)[:depth]
            )
            for name, side in (("bids", "buy"), ("asks", "sell"))
        }
