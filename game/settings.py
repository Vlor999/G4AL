"""Game-wide constants and settings."""

# ── Core ────────────────────────────────────────────────────────────────
FPS = 60

# ── Tile / Map ───────────────────────────────────────────────────────────
TILE_SIZE = 64  # pixels per tile side
MAP_COLS = 30  # map width  in tiles
MAP_ROWS = 20  # map height in tiles
MAP_WIDTH = MAP_COLS * TILE_SIZE
MAP_HEIGHT = MAP_ROWS * TILE_SIZE

# ── Colors (Clash-of-Clans inspired palette) ────────────────────────────
COLOR_GRASS_LIGHT = (124, 179, 66)
COLOR_GRASS_DARK = (104, 159, 56)
COLOR_DIRT = (161, 136, 100)
COLOR_WATER = (66, 165, 245)
COLOR_SAND = (220, 200, 140)

COLOR_TREE_TRUNK = (121, 85, 61)
COLOR_TREE_LEAVES = (56, 142, 60)
COLOR_ROCK_BODY = (158, 158, 158)
COLOR_ROCK_SHADE = (117, 117, 117)
COLOR_GOLD = (255, 215, 0)

COLOR_NPC_BODY = (255, 183, 77)  # orange worker
COLOR_NPC_OUTLINE = (230, 126, 34)
COLOR_NPC_SELECTED = (0, 230, 118)

COLOR_UI_BG = (38, 50, 56)
COLOR_UI_TEXT = (255, 255, 255)
COLOR_UI_BUTTON = (69, 90, 100)
COLOR_UI_BUTTON_HOV = (96, 125, 139)
COLOR_UI_PANEL = (55, 71, 79)
COLOR_HP_GREEN = (76, 175, 80)
COLOR_HP_RED = (244, 67, 54)

# ── NPC ──────────────────────────────────────────────────────────────────
NPC_SPEED = 2.5  # pixels / frame
NPC_MAX_HEALTH = 100
NPC_CHOP_TIME = 600  # frames to chop a tree
NPC_MINE_TIME = 600  # frames to mine a rock
NPC_BUILD_TIME = 900  # frames to build a structure
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
NPC_COLLECT_UNIT_TIME = 90   # frames to harvest 1 unit of any resource (1.5 s)

# ── Archer ───────────────────────────────────────────────────────────────
ARCHER_SHOOT_TIME = 96       # frames for full shoot cycle (aim + fire)
ARCHER_FIRE_ANIM_TIME = 24   # frames of the actual shoot animation (end of cycle)
ARCHER_RANGE = 1             # tiles – max distance to shoot an enemy (melee-range)
ARCHER_ARROW_DAMAGE = 12     # HP per arrow hit
ARCHER_ARROW_FLIGHT = 24     # frames for an arrow to reach the target
ARCHER_DEFEND_SCAN_RADIUS = 6  # tiles – how far a defending archer detects enemies

# ── Wild Archer (enemy AI) ───────────────────────────────────────────────
WILD_ARCHER_RANGE = 1        # tiles – attack range for wild archers
WILD_ARCHER_DAMAGE = 8       # HP per arrow hit on our units
WILD_ARCHER_SHOOT_TIME = 80  # frames between shots (~1.3 s)

# ── Storage Hut (deposit point for carried resources) ────────────────────
STORAGE_HUT_COL = MAP_COLS // 2 - 1   # tile column of the hut origin
STORAGE_HUT_ROW = MAP_ROWS // 2 + 1   # tile row    of the hut origin

# ── Storage capacity ─────────────────────────────────────────────────────
STORAGE_BASE_CAPACITY  = 50   # max total resource units in the initial hut
HOUSE_CAPACITY_BONUS   = 20   # extra capacity per completed house

# ── Building ─────────────────────────────────────────────────────────────
BUILD_COST_WOOD = 5
BUILD_COST_STONE = 3

# ── TTS ──────────────────────────────────────────────────────────────────
TTS_MAX_SPEAKERS = 1  # max NPCs that speak aloud per command (0 = mute)
