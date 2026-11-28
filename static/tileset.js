/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Tiny Swords tilemap: tile names and sheet geometry
   ═══════════════════════════════════════════════════════════════════════════ */

// Every Terrain/Tileset/Tilemap_colorN.png shares this layout. Index = row * 9 + col;
// the comment after each entry is the community guide id, then the tile's role.
// docs/tileset.md lists every index, empty cells included; scripts/tileset_reference.py
// reads this block, so keep one entry per line.
const TILESET_TILE = Object.freeze({
    FLAT_TOP_LEFT: 0, // FG1
    FLAT_TOP: 1, // FG2
    FLAT_TOP_RIGHT: 2, // FG3
    FLAT_STRIP_TOP: 3, // FG13 Top end of a one-tile-wide vertical strip.
    ELEVATED_TOP_LEFT: 5, // EG1
    ELEVATED_TOP: 6, // EG2
    ELEVATED_TOP_RIGHT: 7, // EG3
    ELEVATED_STRIP_TOP: 8, // EG13 Also covers the seam of an east or west drop.
    FLAT_LEFT: 9, // FG4
    FLAT_CENTER: 10, // FG5
    FLAT_RIGHT: 11, // FG6
    FLAT_STRIP_MIDDLE: 12, // FG14
    ELEVATED_LEFT: 14, // EG4
    ELEVATED_CENTER: 15, // EG5 Also replaces the platform edge a ramp leans on.
    ELEVATED_RIGHT: 16, // EG6
    ELEVATED_STRIP_MIDDLE: 17, // EG14
    FLAT_BOTTOM_LEFT: 18, // FG7
    FLAT_BOTTOM: 19, // FG8
    FLAT_BOTTOM_RIGHT: 20, // FG9
    FLAT_STRIP_BOTTOM: 21, // FG15
    ELEVATED_BOTTOM_LEFT: 23, // EG7 Bottom edge of a platform; rock shows under the grass, the cliff face goes on the row below.
    ELEVATED_BOTTOM: 24, // EG8
    ELEVATED_BOTTOM_RIGHT: 25, // EG9
    ELEVATED_STRIP_BOTTOM: 26, // EG15
    FLAT_HORIZONTAL_LEFT: 27, // FG10 Left end of a one-tile-high horizontal run.
    FLAT_HORIZONTAL_MIDDLE: 28, // FG11
    FLAT_HORIZONTAL_RIGHT: 29, // FG12
    FLAT_ISLAND: 30, // FG16 A single tile with no neighbour of its kind.
    ELEVATED_HORIZONTAL_LEFT: 32, // EG10 One-tile-high run, rounded top edge: used when the cell to the north is water.
    ELEVATED_HORIZONTAL_MIDDLE: 33, // EG11
    ELEVATED_HORIZONTAL_RIGHT: 34, // EG12
    ELEVATED_ISLAND: 35, // EG16
    RAMP_LEFT_TOP: 36, // ST25 Ramp on the west side of a platform, climbing east; half the cell is empty.
    RAMP_RIGHT_TOP: 39, // ST28 Ramp on the east side of a platform, climbing west.
    CLIFF_FACE_LEFT_LAND: 41, // EG17 Cliff face above walkable ground, rounded west end.
    CLIFF_FACE_MIDDLE_LAND: 42, // EG18 Also the optional backdrop behind a ramp top.
    CLIFF_FACE_RIGHT_LAND: 43, // EG19
    CLIFF_FACE_NARROW_LAND: 44, // EG20
    RAMP_LEFT_BOTTOM: 45, // ST29 Landing cell of the west ramp, rock at its east edge.
    RAMP_RIGHT_BOTTOM: 48, // ST32
    CLIFF_FACE_LEFT_WATER: 50, // EG21 Cliff face standing in water: same face, pale foam line at its foot.
    CLIFF_FACE_MIDDLE_WATER: 51, // EG22
    CLIFF_FACE_RIGHT_WATER: 52, // EG23
    CLIFF_FACE_NARROW_WATER: 53, // EG24
});

const TILESET_COLUMN_COUNT = 9;
const TILESET_TILE_SIZE = 64;

(function (G) {
    "use strict";

    // Top-left corner, in sheet pixels, of the cell of a TILESET_TILE index.
    G.locateTilesetTile = function (tileIndex) {
        return {
            sourceX: (tileIndex % TILESET_COLUMN_COUNT) * TILESET_TILE_SIZE,
            sourceY: Math.floor(tileIndex / TILESET_COLUMN_COUNT) * TILESET_TILE_SIZE,
        };
    };

})(window.G4AL);
