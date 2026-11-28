# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
"""Write the sprite inventory of ``static/assets/`` to ``docs/assets.md``.

Run from the repository root: ``uv run --script scripts/asset_inventory.py``.
It measures every PNG, reads frame counts from ``static/assets/details.js`` and the
loaded paths from ``static/sprites.js`` and ``static/style.css``, and joins the footprint and height of each
object kind from ``game/world/dimensions.py``.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

from game.settings import TILE_SIZE  # noqa: E402
from game.world.dimensions import OBJECT_DIMENSIONS, ObjectKind  # noqa: E402

ASSETS_DIRECTORY = REPOSITORY_ROOT / "static" / "assets"
DETAILS_FILE = ASSETS_DIRECTORY / "details.js"
SPRITES_FILE = REPOSITORY_ROOT / "static" / "sprites.js"
STYLE_FILE = REPOSITORY_ROOT / "static" / "style.css"
OUTPUT_FILE = REPOSITORY_ROOT / "docs" / "assets.md"
SEPARATELY_LISTED_DIRECTORIES = ("lechat/", "UI Elements/")
TILEMAP_PATH_PREFIX = "Terrain/Tileset/Tilemap_color"
TILE_INDEX_LINK = " ([tile index](tileset.md))"

DETAILS_ENTRY = re.compile(r"^\s{4}(\w+): \{")
DETAILS_FRAMES = re.compile(r"frames: (\d+)")
DETAILS_PATH = re.compile(r'"static/assets/([^"]+\.png)"')
STYLE_PATH = re.compile(r"url\(['\"]?assets/([^'\")]+\.png)")
SPRITES_PATH = re.compile(r'loadImg\("\w+",\s*"([^"]+\.png)"\)')
SPRITES_TEMPLATE = re.compile(r'"(\w+/\w+_)" \+ String\(i\)\.padStart\((\d+), "0"\) \+ "\.png"')
SPRITES_TEMPLATE_LENGTH = re.compile(r"G\.catFrameCount = (\d+);")

# Which object kind of the game a sprite draws; the first matching prefix wins.
KIND_BY_PATH_PREFIX: tuple[tuple[str, ObjectKind], ...] = (
    ("Buildings/Blue Buildings/House1", ObjectKind.HOUSE1),
    ("Buildings/Blue Buildings/House2", ObjectKind.HOUSE2),
    ("Buildings/Blue Buildings/House3", ObjectKind.HOUSE3),
    ("Buildings/Blue Buildings/Castle", ObjectKind.CASTLE),
    ("Buildings/Blue Buildings/Barracks", ObjectKind.BARRACKS),
    ("Buildings/Blue Buildings/Archery", ObjectKind.ARCHERY),
    ("Buildings/Blue Buildings/Tower", ObjectKind.TOWER),
    ("Buildings/Blue Buildings/Monastery", ObjectKind.MONASTERY),
    ("Terrain/Resources/Wood/Trees/Tree", ObjectKind.TREE),
    ("Terrain/Decorations/Rocks/Rock", ObjectKind.ROCK),
    ("Terrain/Resources/Gold/Gold Stones/Gold Stone", ObjectKind.GOLD_ROCK),
    ("Terrain/Resources/Meat/Sheep/", ObjectKind.SHEEP),
    ("Units/Blue Units/Pawn/", ObjectKind.PAWN),
    ("Units/Blue Units/Archer/Archer_", ObjectKind.ARCHER),
    ("Units/Red Units/Archer/Archer_", ObjectKind.WILD_ARCHER),
    ("lechat/", ObjectKind.CAT),
)

# Why an unused PNG stays on disk: the feature it is kept for; the first matching prefix wins.
FEATURE_BY_UNUSED_PATH_PREFIX: tuple[tuple[str, str], ...] = (
    ("Particle FX/Explosion", "combat effects (explosions)"),
    ("Particle FX/Fire_03", "fire effect for burning structures"),
    ("Particle FX/Water Splash", "water effects (an NPC or object falling in water)"),
    ("Terrain/Decorations/Rubber Duck", "water decoration"),
    ("Terrain/Resources/Tools/", "tool icons (pickaxe, axe, hammer) for the interface"),
    ("Terrain/Resources/", "resource icons for storage and carried loads"),
    ("UI Elements/UI Elements/Icons/", "interface icons (order panel, NPC status)"),
    ("Units/Blue Units/Lancer/", "future unit type: lancer"),
    ("Units/Blue Units/Monk/", "future unit type: monk (healer)"),
    ("Units/Blue Units/Warrior/", "future unit type: warrior"),
    ("Units/Blue Units/Pawn/", "pawn knife run animation (hunting)"),
)
UNASSIGNED_FEATURE = "no intended feature recorded"


@dataclass(frozen=True)
class SpriteMeasure:
    path: str
    sheet_width: int
    sheet_height: int
    frame_count: int
    opaque_box: tuple[int, int, int, int] | None

    @property
    def frame_width(self) -> int:
        return self.sheet_width // self.frame_count

    @property
    def anchor(self) -> str:
        if self.opaque_box is None:
            return "-"
        left, _, right, bottom = self.opaque_box
        return f"({(left + right) // 2}, {bottom})"

    @property
    def opaque_height_in_tiles(self) -> str:
        if self.opaque_box is None:
            return "-"
        return f"{(self.opaque_box[3] - self.opaque_box[1]) / TILE_SIZE:.2f}"


def read_frame_counts() -> dict[str, int]:
    """Frame count per PNG path (relative to ``static/assets/``) declared in details.js."""
    frame_counts: dict[str, int] = {}
    frames = 1
    for line in DETAILS_FILE.read_text(encoding="utf-8").splitlines():
        if DETAILS_ENTRY.match(line):
            frames = 1
        if frames_match := DETAILS_FRAMES.search(line):
            frames = int(frames_match.group(1))
        for path in DETAILS_PATH.findall(line):
            frame_counts[path] = frames
    return frame_counts


def read_loaded_paths() -> set[str]:
    """PNG paths (relative to ``static/assets/``) the client loads in sprites.js or style.css."""
    source = SPRITES_FILE.read_text(encoding="utf-8")
    paths = set(SPRITES_PATH.findall(source))
    paths.update(unquote(path) for path in STYLE_PATH.findall(STYLE_FILE.read_text("utf-8")))
    template = SPRITES_TEMPLATE.search(source)
    length = SPRITES_TEMPLATE_LENGTH.search(source)
    if template and length:
        prefix, width = template.group(1), int(template.group(2))
        paths.update(f"{prefix}{index:0{width}d}.png" for index in range(int(length.group(1))))
    return paths


def find_frame_count(frame_counts: dict[str, int], path: str) -> int:
    # The red units are not in details.js: the renderer draws them with the blue counts.
    blue_path = path.replace("Red Units/", "Blue Units/")
    return frame_counts.get(path, frame_counts.get(blue_path, 1))


def measure(path: str, frame_count: int) -> SpriteMeasure:
    # Imported here so the tests can import this module without Pillow installed.
    from PIL import Image

    with Image.open(ASSETS_DIRECTORY / path) as image:
        width, height = image.size
        first_frame = image.convert("RGBA").crop((0, 0, width // frame_count, height))
        opaque_box = first_frame.getchannel("A").getbbox()
    return SpriteMeasure(path, width, height, frame_count, opaque_box)


def kind_of(path: str) -> ObjectKind | None:
    for prefix, kind in KIND_BY_PATH_PREFIX:
        if path.startswith(prefix):
            return kind
    return None


def format_dimensions(path: str) -> tuple[str, str]:
    kind = kind_of(path)
    if kind is None:
        return "-", "-"
    dimensions = OBJECT_DIMENSIONS[kind]
    footprint = f"{dimensions.footprint_width}×{dimensions.footprint_depth}"
    return f"{kind.value} {footprint}", f"{dimensions.height:g}"


def format_row(sprite: SpriteMeasure) -> str:
    kind_and_footprint, height = format_dimensions(sprite.path)
    link = TILE_INDEX_LINK if sprite.path.startswith(TILEMAP_PATH_PREFIX) else ""
    return (
        f"| `{sprite.path}`{link} | {sprite.sheet_width}×{sprite.sheet_height} | {sprite.frame_count} "
        f"| {sprite.frame_width}×{sprite.sheet_height} | {sprite.opaque_box or '-'} "
        f"| {sprite.anchor} | {sprite.opaque_height_in_tiles} | {kind_and_footprint} | {height} |"
    )


TABLE_HEADER = (
    "| Path | Sheet (px) | Frames | Frame (px) | Opaque box of frame 0 (px) "
    "| Anchor (px) | Opaque height (tiles) | Kind and footprint (tiles) | Height (tiles) |\n"
    "|---|---|---|---|---|---|---|---|---|"
)


def group_by_feature(paths: list[str]) -> dict[str, list[str]]:
    """Group the unused PNG paths by the feature they are kept for."""
    groups: dict[str, list[str]] = {}
    for path in paths:
        feature = next(
            (name for prefix, name in FEATURE_BY_UNUSED_PATH_PREFIX if path.startswith(prefix)),
            UNASSIGNED_FEATURE,
        )
        groups.setdefault(feature, []).append(path)
    return groups


def render_unused(unused: list[str]) -> list[str]:
    lines: list[str] = []
    for feature, paths in group_by_feature(unused).items():
        lines += [
            f"### {feature[0].upper()}{feature[1:]}",
            "",
            *[f"- `{path}`" for path in paths],
            "",
        ]
    return lines[:-1] or ["None."]


def render(sprites: list[SpriteMeasure], *, unused: list[str], missing: list[str]) -> str:
    game_rows = [
        format_row(s) for s in sprites if not s.path.startswith(SEPARATELY_LISTED_DIRECTORIES)
    ]
    other_rows = [
        format_row(s) for s in sprites if s.path.startswith(SEPARATELY_LISTED_DIRECTORIES)
    ]
    sections = [
        "# Asset inventory",
        "",
        "Generated by `uv run --script scripts/asset_inventory.py`; do not edit by hand.",
        f"Paths are relative to `static/assets/`. One tile is {TILE_SIZE} px. The frame count",
        "comes from `details.js` (1 when the sheet is not listed there). The anchor is the",
        "bottom centre of the opaque box of frame 0: where the object touches the ground.",
        "Footprint and height are the values of `game/world/dimensions.py` for the object kind the",
        "sprite draws (decision in `docs/adr/0002-object-dimensions-and-height-model.md`).",
        "",
        "## Game sprites",
        "",
        TABLE_HEADER,
        *game_rows,
        "",
        "## Le Chat frames and UI elements",
        "",
        TABLE_HEADER,
        *other_rows,
        "",
        "## Unused PNGs",
        "",
        "On disk, not loaded by `static/sprites.js` or `static/style.css`. Kept on purpose, grouped by the",
        "feature each group is for.",
        "",
        *render_unused(unused),
        "",
        "## Referenced but missing on disk",
        "",
        "Paths in `details.js`, `static/sprites.js` or `static/style.css` with no file.",
        "",
        *([f"- `{path}`" for path in missing] or ["None."]),
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    frame_counts = read_frame_counts()
    loaded = read_loaded_paths()
    on_disk = sorted(
        str(path.relative_to(ASSETS_DIRECTORY)) for path in ASSETS_DIRECTORY.rglob("*.png")
    )
    sprites = [measure(path, find_frame_count(frame_counts, path)) for path in on_disk]
    on_disk_set = set(on_disk)
    OUTPUT_FILE.write_text(
        render(
            sprites,
            unused=[path for path in on_disk if path not in loaded],
            missing=sorted((loaded | set(frame_counts)) - on_disk_set),
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
