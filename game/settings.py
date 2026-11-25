"""Game-wide constants and settings."""

from game.terrain import Biome

# ── Core ────────────────────────────────────────────────────────────────
FPS = 60

# ── Tile / Map ───────────────────────────────────────────────────────────
TILE_SIZE = 64  # pixels per tile side
MAP_COLS = 30  # map width  in tiles
MAP_ROWS = 20  # map height in tiles

# ── Biomes (docs/adr/0003-biome-map-generation.md) ───────────────────────
BIOME_REGION_COUNTS = {Biome.MEADOW: 3, Biome.FOREST: 4, Biome.HIGHLAND: 3}  # Voronoi seeds
BIOME_BORDER_JITTER = 6.0  # squared tiles of noise on each seed distance: ragged borders
BIOME_EDGE_MARGIN = 2  # tiles between the map edge and a region seed or a lake centre
HOME_MEADOW_RADIUS = 4  # tiles around the map centre kept meadow, without water
LAKE_COUNT = 3
LAKE_RADIUS_RANGE = (1, 2)  # tiles of water around a lake centre
LAKE_SHORE_WIDTH = 1  # tiles of sand around the water
DIRT_PATCH_COUNTS = {Biome.MEADOW: 3, Biome.FOREST: 1, Biome.HIGHLAND: 5}
DIRT_PATCH_RADIUS_RANGE = (1, 2)
# Chance that a free walkable tile of the biome gets the resource
TREE_DENSITY = {Biome.MEADOW: 0.02, Biome.FOREST: 0.3, Biome.HIGHLAND: 0.02, Biome.LAKE: 0.0}
ROCK_DENSITY = {Biome.MEADOW: 0.01, Biome.FOREST: 0.01, Biome.HIGHLAND: 0.15, Biome.LAKE: 0.0}
GOLD_ROCK_SHARE = {Biome.MEADOW: 0.0, Biome.FOREST: 0.0, Biome.HIGHLAND: 0.35, Biome.LAKE: 0.0}
SHEEP_BIOMES = frozenset({Biome.MEADOW})  # where sheep spawn when such a grass tile is free

# ── NPC ──────────────────────────────────────────────────────────────────
NPC_SPEED = 2.5  # pixels / frame
NPC_MAX_HEALTH = 100
NPC_BUILD_TIME = 2000  # frames to build a structure
NPC_HUNGER_MAX = 100
NPC_HUNGER_DRAIN = 0.005  # hunger lost per frame (≈ 1 per ~67 frames ≈ ~1.1s at 60 fps)
NPC_EAT_TIME = 60  # frames to eat
NPC_EAT_RESTORE = 35  # hunger restored when eating
EAT_WHEAT_COST = 2  # wheat consumed per eat action
NPC_HUNGER_DAMAGE = 0.05  # HP lost per frame when hunger == 0

# ── Resources ────────────────────────────────────────────────────────────
TREE_WOOD_YIELD = 10
ROCK_STONE_YIELD = 8
ROCK_GOLD_YIELD = 3
WHEAT_YIELD = 5  # wheat per fully grown field
WHEAT_GROW_TIME = 300  # frames to grow (5 s at 60 fps)
WHEAT_PLANT_TIME = 60  # frames to plant

# ── Per-unit resource collection ──────────────────────────────────────────
NPC_COLLECT_UNIT_TIME = 90  # frames to harvest 1 unit of any resource (1.5 s)

# ── Archer ───────────────────────────────────────────────────────────────
# Keep 0 < ARCHER_FIRE_ANIM_TIME < ARCHER_SHOOT_TIME: Archer._perform relies on the
# shot landing before the shoot cycle ends.
ARCHER_SHOOT_TIME = 96  # frames for full shoot cycle (aim + fire)
ARCHER_FIRE_ANIM_TIME = 24  # frames of the actual shoot animation (end of cycle)
ARCHER_RANGE = 1  # tiles – max distance to shoot an enemy (melee-range)
ARCHER_ARROW_DAMAGE = 12  # HP per arrow hit
ARCHER_ARROW_FLIGHT = 24  # frames for an arrow to reach the target
ARCHER_DEFEND_SCAN_RADIUS = 6  # tiles – how far a defending archer detects enemies

# ── Wild Archer (enemy AI) ───────────────────────────────────────────────
WILD_ARCHER_RANGE = 1  # tiles – attack range for wild archers
WILD_ARCHER_CHASE_RANGE = 6  # tiles – a wild archer chases an NPC this close
WILD_ARCHER_DAMAGE = 8  # HP per arrow hit on our units
WILD_ARCHER_SHOOT_TIME = 80  # frames between shots (~1.3 s)
WILD_ARCHER_GRACE_FRAMES = 7200  # world frames (2 min) at game start before wild archers attack

# ── Storage Hut (deposit point for carried resources) ────────────────────
STORAGE_HUT_COL = MAP_COLS // 2 - 1  # tile column of the hut origin
STORAGE_HUT_ROW = MAP_ROWS // 2  # tile row    of the hut origin

# ── Initial spawn ────────────────────────────────────────────────────────
INITIAL_PAWN_COUNT = 3
PAWN_SPAWN_RADIUS = 3  # tiles around the map centre searched for pawn spots
INITIAL_ARCHER_COUNT = 2
ARCHER_SPAWN_MAX_DISTANCE = 5  # tiles: outermost ring around the hut searched for archers
INITIAL_SHEEP_COUNT = 6
INITIAL_WILD_ARCHER_COUNT = 3
WILD_ARCHER_CORNER_MARGIN = 3  # tiles between the map edge and the wild archer camp centre
WILD_ARCHER_SPAWN_RADIUS = 3  # tiles around the camp centre searched for wild archers

# ── Storage capacity ─────────────────────────────────────────────────────
STORAGE_BASE_CAPACITY = 50  # max total resource units in the initial hut
HOUSE_CAPACITY_BONUS = 20  # extra capacity per completed house

# ── Building ─────────────────────────────────────────────────────────────
BUILD_COST_WOOD = 5
BUILD_COST_STONE = 3

# ── TTS ──────────────────────────────────────────────────────────────────
TTS_MAX_SPEAKERS = 1  # max NPCs that speak aloud per command (0 = mute)
ORDER_SPEECH_DURATION_FRAMES = 360  # speech bubble of an NPC answering a voice order
