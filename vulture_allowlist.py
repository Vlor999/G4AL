"""Names vulture reports as unused but that are read where it cannot see.

Vulture reads attribute access only. The keys below are read by subscription
(`arrow["fromX"]`) in `server/` and by the client in `static/` through the state JSON.
"""

from vulture.whitelist_utils import Whitelist

_ = Whitelist()

# game/combat/arrows.py, Arrow: read as dict keys by server/serialization.py and server/engine.py,
# then by static/renderer.js.
_.fromX
_.fromY
_.toX
_.toY
_.frame
_.totalFrames
_.team

# game/resources/storage.py, StorageSnapshot: key of the "storage" object in the state the server
# sends (GET /api/state, Socket.IO "state"), read by static/ui.js.
_.houseCount

# game/world/npc_names.py, ArcherName and WildArcherName: members read by iterating the enum to
# build the name pools.
_.ROBIN
_.ARTEMIS
_.HAWKE
_.FLETCHER
_.YGRITTE
_.LEGOLAS
_.BANDIT
_.OUTLAW
_.ROGUE
_.POACHER
_.MARAUDER
_.RAIDER
