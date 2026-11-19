"""Meaningful domain literals that are not game tuning (tuning lives in ``settings.py``)."""

STORED_RESOURCE_KINDS: tuple[str, ...] = ("wood", "stone", "gold", "wheat")

ARROW_LAUNCH_HEIGHT = 20  # pixels above the shooter's position: the bow
ARROW_IMPACT_HEIGHT = 10  # pixels above the target's position: the body
