/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Map image: ground tiles drawn once, decorations and clouds placed
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // Tile codes of the state's map.tiles, mirroring game/world/terrain.py TileType.
    const TILE_TYPE = { GRASS: 0, DIRT: 1, SAND: 2, WATER: 3 };

    const TILE_COLORS = {
        [TILE_TYPE.GRASS]: { light: "#7cb342", dark: "#689f38" },
        [TILE_TYPE.DIRT]: { light: "#a18864", dark: "#a18864" },
        [TILE_TYPE.SAND]: { light: "#dcc88c", dark: "#dcc88c" },
        [TILE_TYPE.WATER]: { light: "#42a5f5", dark: "#42a5f5" },
    };

    // Ground and decorations per biome (docs/adr/0003-biome-map-generation.md).
    const GRASS_TILESET_BY_BIOME = {
        meadow: "ts_grass", forest: "ts_forest", highland: "ts_highland", lake: "ts_grass",
    };
    const BUSH_ONE_TILE_IN_BY_BIOME = { meadow: 30, forest: 8 };

    G.mapLayers = { canvas: null, decorations: [], waterRocks: [], clouds: [] };

    // ── Map builder ─────────────────────────────────────────────────────

    G.buildMapImage = function () {
        if (!G.mapCached) return;
        const { cols, rows, tileSize, tiles, biomes } = G.mapCached;
        const sprites = G.sprites;
        const posHash = G.posHash;

        const mapCanvas = document.createElement("canvas");
        mapCanvas.width = cols * tileSize;
        mapCanvas.height = rows * tileSize;
        const mctx = mapCanvas.getContext("2d");
        const decorations = [];
        const waterRocks = [];

        const groundTile = G.locateTilesetTile(TILESET_TILE.FLAT_CENTER);

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const tt = tiles[r][c];
                const biome = biomes[r][c];
                const px = c * tileSize;
                const py = r * tileSize;

                let tileset = null;
                if (tt === TILE_TYPE.GRASS) tileset = sprites[GRASS_TILESET_BY_BIOME[biome]] || sprites.ts_grass;
                else if (tt === TILE_TYPE.DIRT) tileset = sprites.ts_dirt;
                else if (tt === TILE_TYPE.SAND) tileset = sprites.ts_sand;
                else if (tt === TILE_TYPE.WATER) {
                    if (sprites.water_bg) {
                        mctx.drawImage(sprites.water_bg, px, py, tileSize, tileSize);
                    } else {
                        mctx.fillStyle = "#42a5f5";
                        mctx.fillRect(px, py, tileSize, tileSize);
                    }
                    if (posHash(c + 5, r + 7, 12) === 0) {
                        waterRocks.push({
                            variant: posHash(c, r, 4) + 1,
                            x: px + tileSize / 2,
                            y: py + tileSize / 2,
                        });
                    }
                    continue;
                }

                if (tileset) {
                    mctx.drawImage(
                        tileset, groundTile.sourceX, groundTile.sourceY, TILESET_TILE_SIZE, TILESET_TILE_SIZE,
                        px, py, tileSize, tileSize,
                    );
                    if ((r + c) % 2 === 0) {
                        mctx.fillStyle = "rgba(0,0,0,0.04)";
                        mctx.fillRect(px, py, tileSize, tileSize);
                    }
                } else {
                    const colors = TILE_COLORS[tt] || TILE_COLORS[TILE_TYPE.GRASS];
                    const color = (r + c) % 2 === 0 ? colors.light : colors.dark;
                    mctx.fillStyle = color;
                    mctx.fillRect(px, py, tileSize, tileSize);
                }

                const bushOneTileIn = BUSH_ONE_TILE_IN_BY_BIOME[biome];
                if (tt === TILE_TYPE.GRASS && bushOneTileIn && posHash(c + 1, r + 3, bushOneTileIn) === 0) {
                    decorations.push({
                        type: "bush",
                        variant: posHash(c, r, 4) + 1,
                        offset: posHash(c + r, r * c, 8),
                        x: px + tileSize / 2,
                        y: py + tileSize / 2,
                    });
                }
            }
        }

        // Floating clouds
        const clouds = [];
        const mapW = cols * tileSize;
        const mapH = rows * tileSize;
        const cloudCount = Math.floor(cols * rows / 40);
        for (let i = 0; i < cloudCount; i++) {
            clouds.push({
                variant: posHash(i, i * 3 + 7, 8) + 1,
                x: posHash(i * 7, i * 13, mapW),
                y: posHash(i * 11, i * 5, mapH),
                speed: 0.15 + posHash(i, i + 99, 100) / 500,
                scale: 0.8 + posHash(i + 3, i * 2, 40) / 100,
            });
        }
        G.mapLayers = { canvas: mapCanvas, decorations, waterRocks, clouds };
    };

})(window.G4AL);
