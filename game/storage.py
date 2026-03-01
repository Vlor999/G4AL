"""Global resource stockpile – shared by all bots, Clash-of-Clans style."""

from __future__ import annotations

from game.settings import STORAGE_BASE_CAPACITY, HOUSE_CAPACITY_BONUS


class ResourceStorage:
    """Singleton-like global inventory for the settlement."""

    def __init__(self):
        self._stock: dict[str, int] = {
            "wood": 0,
            "stone": 0,
            "gold":  0,
            "wheat": 0,
        }
        self._house_count: int = 0  # completed houses (excluding storage hut)

    # ── capacity ─────────────────────────────────────────────────────────

    @property
    def capacity(self) -> int:
        """Maximum total resource units that can be stored."""
        return STORAGE_BASE_CAPACITY + self._house_count * HOUSE_CAPACITY_BONUS

    @property
    def total(self) -> int:
        """Current total resource units stored."""
        return sum(self._stock.values())

    @property
    def is_full(self) -> bool:
        return self.total >= self.capacity

    @property
    def remaining_space(self) -> int:
        return max(0, self.capacity - self.total)

    def register_house(self):
        """Call when a new house is completed to increase capacity."""
        self._house_count += 1

    # ── public API ───────────────────────────────────────────────────────
    def add(self, resource: str, amount: int) -> int:
        """Add resources. Returns the amount actually stored (may be capped)."""
        self._stock.setdefault(resource, 0)
        space = self.remaining_space
        actual = min(amount, space)
        self._stock[resource] += actual
        return actual

    def spend(self, resource: str, amount: int) -> bool:
        """Try to spend. Returns True on success, False if insufficient."""
        if self._stock.get(resource, 0) >= amount:
            self._stock[resource] -= amount
            return True
        return False

    def get(self, resource: str) -> int:
        return self._stock.get(resource, 0)

    @property
    def wood(self) -> int:
        return self._stock["wood"]

    @property
    def stone(self) -> int:
        return self._stock["stone"]

    @property
    def gold(self) -> int:
        return self._stock["gold"]

    @property
    def wheat(self) -> int:
        return self._stock["wheat"]

    def snapshot(self) -> dict:
        return {
            **self._stock,
            "capacity": self.capacity,
            "total": self.total,
            "houseCount": self._house_count,
        }

    def __repr__(self):
        return f"Storage({self._stock}, cap={self.capacity})"
