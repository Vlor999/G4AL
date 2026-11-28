"""Game tuning. Durations are in frames and speeds in pixels per frame, at ``FPS``."""

from game.world.terrain import Biome

FPS = 60

TILE_SIZE = 64  # pixels per tile side
MAP_COLS = 30  # map width  in tiles
MAP_ROWS = 20  # map height in tiles

# Map generation: docs/adr/0003-biome-map-generation.md
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

NPC_SPEED = 2.5
NPC_MAX_HEALTH = 100
NPC_BUILD_TIME = 2000  # frames to build a structure
NPC_HUNGER_MAX = 100
NPC_HUNGER_DRAIN = 0.005  # per frame: a full hunger bar lasts 20 000 frames (~5.5 min)
NPC_EAT_TIME = 60  # frames to eat
NPC_EAT_RESTORE = 35
NPC_PLANT_SEARCH_RADIUS = 5  # tiles searched around the order's tile for a free field
NPC_BUILD_SEARCH_RADIUS = 8  # tiles searched around the order's tile for a free footprint
EAT_WHEAT_COST = 2
NPC_FISH_TIME = 600  # frames of fishing on the shore before the catch (10 s)
NPC_FISH_RESTORE = 25  # hunger the catch restores: less than eating, but it costs no wheat
NPC_SWIM_TIME = 300  # frames spent in the water tile before swimming back (5 s)
NPC_HUNGER_DAMAGE = 0.05  # HP lost per frame when hunger == 0

DEFAULT_SPEECH_DURATION_FRAMES = 300
BRIEF_SPEECH_DURATION_FRAMES = 60  # a combat shout
SHORT_SPEECH_DURATION_FRAMES = 90  # a status line
MEDIUM_SPEECH_DURATION_FRAMES = 120  # an order the pawn cannot carry out
LONG_SPEECH_DURATION_FRAMES = 180  # a refusal the player must notice
ORDER_SPEECH_DURATION_FRAMES = 360  # speech bubble of an NPC answering a voice order

TREE_WOOD_YIELD = 10
ROCK_STONE_YIELD = 8
ROCK_GOLD_YIELD = 3
WHEAT_YIELD = 5  # wheat per fully grown field
WHEAT_GROW_TIME = 300  # frames to grow (5 s at 60 fps)
WHEAT_PLANT_TIME = 60  # frames to plant

NPC_COLLECT_UNIT_TIME = 90  # frames to harvest 1 unit of any resource (1.5 s)

TREE_MAX_HP = TREE_WOOD_YIELD * 3
ROCK_MAX_HP = ROCK_STONE_YIELD * 4
STRUCTURE_MAX_HP = 100
WHEAT_FIELD_MAX_HP = 10

# Keep 0 < ARCHER_FIRE_ANIM_TIME < ARCHER_SHOOT_TIME: Archer._advance_shot relies on the
# shot landing before the shoot cycle ends.
ARCHER_SHOOT_TIME = 96  # frames for full shoot cycle (aim + fire)
ARCHER_FIRE_ANIM_TIME = 24  # frames of the actual shoot animation (end of cycle)
ARCHER_RANGE = 1  # tiles – max distance to shoot an enemy (melee-range)
ARCHER_ARROW_DAMAGE = 12  # HP per arrow hit
ARCHER_ARROW_FLIGHT = 24  # frames for an arrow to reach the target
ARCHER_DEFEND_SCAN_RADIUS = 6  # tiles – how far a defending archer detects enemies
ARCHER_SPEED = NPC_SPEED * 1.1
ARCHER_MAX_HEALTH = 70

FAUNA_WANDER_RADIUS = 5  # tiles around its tile a creature wanders to
FAUNA_MAX_HEALTH = 30
FAUNA_SPEED = 1.0
FAUNA_IDLE_DURATION_RANGE = (60, 240)  # frames
FAUNA_GRAZE_DURATION_RANGE = (120, 360)  # frames
FAUNA_GRAZE_CHANCE = 0.5  # chance that an idle creature grazes rather than wanders
SHEEP_MAX_HEALTH = 20
SHEEP_SPEED = 0.8
CAT_MAX_HEALTH = 50
CAT_SPEED = 0.0  # the cat never leaves its tile
CAT_CORNER_MARGIN = 2  # tiles between the map edge and the cat's corner tile

WILD_ARCHER_RANGE = 1  # tiles – attack range for wild archers
WILD_ARCHER_CHASE_RANGE = 6  # tiles – a wild archer chases an NPC this close
WILD_ARCHER_DAMAGE = 8  # HP per arrow hit on an NPC
WILD_ARCHER_SHOOT_TIME = 80  # frames between shots (~1.3 s)
WILD_ARCHER_GRACE_FRAMES = 7200  # world frames (2 min) at game start before wild archers attack
WILD_ARCHER_WANDER_RADIUS = 8  # tiles
WILD_ARCHER_MAX_HEALTH = 50
WILD_ARCHER_SPEED = 1.5
WILD_ARCHER_WANDER_CHANCE = 0.35  # chance that an idle wild archer with no target wanders
WILD_ARCHER_IDLE_DURATION_RANGE = (90, 300)  # frames

INITIAL_PAWN_COUNT = 3
PAWN_SPAWN_RADIUS = 3  # tiles around the map centre searched for pawn spots
INITIAL_ARCHER_COUNT = 2
ARCHER_SPAWN_MAX_DISTANCE = 5  # tiles: outermost ring around the hut searched for archers
INITIAL_SHEEP_COUNT = 6
INITIAL_WILD_ARCHER_COUNT = 3
WILD_ARCHER_CORNER_MARGIN = 3  # tiles between the map edge and the wild archer camp centre
WILD_ARCHER_SPAWN_RADIUS = 3  # tiles around the camp centre searched for wild archers

STORAGE_BASE_CAPACITY = 50  # max total resource units in the initial hut
HOUSE_CAPACITY_BONUS = 20

BUILD_COST_WOOD = 5
BUILD_COST_STONE = 3

TTS_MAX_SPEAKERS = 1  # max NPCs that speak aloud per command (0 = mute)
