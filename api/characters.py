"""Character personality descriptions for each NPC name.

Kept for backward compatibility — the canonical source of truth is now
:pymod:`api.roster`.  Importing ``CHARACTER_SOULS`` or ``get_soul`` from
here still works.
"""

from api.roster import CHARACTER_SOULS, get_soul  # noqa: F401

__all__ = ["CHARACTER_SOULS", "get_soul"]
