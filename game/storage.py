"""Global resource stockpile – shared by all bots, Clash-of-Clans style."""

from __future__ import annotations


class ResourceStorage:
    """Singleton-like global inventory for the settlement."""

    def __init__(self):
        self._stock: dict[str, int] = {
            "wood":  0,
            "stone": 0,
            "gold":  0,
        }

    # ── public API ───────────────────────────────────────────────────────
    def add(self, resource: str, amount: int):
        self._stock.setdefault(resource, 0)
        self._stock[resource] += amount

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

    def snapshot(self) -> dict[str, int]:
        return dict(self._stock)

    def __repr__(self):
        return f"Storage({self._stock})"
