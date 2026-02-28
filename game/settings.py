"""Game-wide constants and settings."""

# ── Display ──────────────────────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "G4AL – Survival"

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
NPC_CHOP_TIME = 90      # frames to chop a tree
NPC_MINE_TIME = 120     # frames to mine a rock
NPC_BUILD_TIME = 180    # frames to build a structure
NPC_HUNGER_MAX = 100
NPC_HUNGER_DRAIN = 0.005     # hunger lost per frame (≈ 1 per ~67 frames ≈ ~1.1s at 60 fps)
NPC_EAT_TIME = 60            # frames to eat
NPC_EAT_RESTORE = 35         # hunger restored when eating
EAT_WHEAT_COST = 2           # wheat consumed per eat action
NPC_HUNGER_DAMAGE = 0.05     # HP lost per frame when hunger == 0

# ── Resources ────────────────────────────────────────────────────────────
TREE_WOOD_YIELD = 10
ROCK_STONE_YIELD = 8
ROCK_GOLD_YIELD = 3
WHEAT_YIELD = 5              # wheat per fully grown field
WHEAT_GROW_TIME = 300        # frames to grow (5 s at 60 fps)
WHEAT_PLANT_TIME = 60        # frames to plant

# ── Building ─────────────────────────────────────────────────────────────
BUILD_COST_WOOD = 5
BUILD_COST_STONE = 3

# ── Camera ───────────────────────────────────────────────────────────────
CAMERA_SPEED = 8  # pixels / frame when scrolling
CAMERA_EDGE_MARGIN = 30  # pixels from screen edge to start scrolling

# ── UI ───────────────────────────────────────────────────────────────────
UI_PANEL_HEIGHT = 160
UI_FONT_SIZE = 18
UI_FONT_SIZE_LARGE = 24

# ── TTS ──────────────────────────────────────────────────────────────────
TTS_MAX_SPEAKERS = 1  # max NPCs that speak aloud per command (0 = mute)
