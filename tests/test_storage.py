import pytest

from game.settings import HOUSE_CAPACITY_BONUS, STORAGE_BASE_CAPACITY
from game.storage import ResourceStorage


def test_capacity_grows_with_each_house() -> None:
    storage = ResourceStorage()
    assert storage.capacity == STORAGE_BASE_CAPACITY
    storage.register_house()
    storage.register_house()
    assert storage.capacity == STORAGE_BASE_CAPACITY + 2 * HOUSE_CAPACITY_BONUS


def test_add_is_capped_by_remaining_space() -> None:
    storage = ResourceStorage()
    storage.add("wood", STORAGE_BASE_CAPACITY - 3)
    stored = storage.add("stone", 10)
    assert stored == 3
    assert storage.stone == 3
    assert storage.is_full
    assert storage.remaining_space == 0


@pytest.mark.parametrize(
    ("amount", "expected_success", "expected_left"),
    [(4, True, 1), (5, True, 0), (6, False, 5)],
)
def test_spend(amount: int, expected_success: bool, expected_left: int) -> None:
    storage = ResourceStorage()
    storage.add("wheat", 5)
    assert storage.spend("wheat", amount) is expected_success
    assert storage.wheat == expected_left


@pytest.mark.parametrize(("amount", "expected_removed"), [(2, 2), (9, 5)])
def test_discard_removes_at_most_the_stock(amount: int, expected_removed: int) -> None:
    storage = ResourceStorage()
    storage.add("gold", 5)
    assert storage.discard("gold", amount) == expected_removed
    assert storage.gold == 5 - expected_removed


def test_snapshot_reports_stock_and_capacity() -> None:
    storage = ResourceStorage()
    storage.add("wood", 2)
    storage.register_house()
    assert storage.snapshot() == {
        "wood": 2,
        "stone": 0,
        "gold": 0,
        "wheat": 0,
        "capacity": STORAGE_BASE_CAPACITY + HOUSE_CAPACITY_BONUS,
        "total": 2,
        "houseCount": 1,
    }
