/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Sprite Loading & Animation System
   ═══════════════════════════════════════════════════════════════════════════ */

window.G4AL = window.G4AL || {};

(function (G) {
    "use strict";

    // ── Shared state (must be first – other modules depend on these) ────
    G.gameState = null;
    G.mapCached = null;
    G.selectedId = null;
    G.camX = 0;
    G.camY = 0;
    G.gameFrame = 0;
    G.keysDown = new Set();

    // ── Canvas refs ─────────────────────────────────────────────────────
    G.canvas = document.getElementById("game-canvas");
    G.ctx = G.canvas.getContext("2d");
    G.container = document.getElementById("canvas-container");

    // ── Resize canvas to fill container ──────────────────────────────────
    function resizeCanvas() {
        G.canvas.width = G.container.clientWidth;
        G.canvas.height = G.container.clientHeight;
    }
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    // ── REST helper (used by input.js event handlers) ───────────────────
    G.postJSON = async function (endpoint, body) {
        try {
            await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
        } catch (e) { console.error(e); }
    };

    // ── Sprite data ─────────────────────────────────────────────────────
    const ASSET = "/static/assets";

    G.sprites = {};
    G.spritesLoaded = false;
    G.npcFacing = {};

    // Speed tiers: game frames per animation frame change
    const ANIM_SPEED = { slow: 30, normal: 12, fast: 5 };
    G.ANIM_SPEED = ANIM_SPEED;

    // ── Config helpers (reads from SPRITE_CONFIG in details.js) ─────────

    function cfgFrames(key, fallback) {
        if (typeof SPRITE_CONFIG !== "undefined" && SPRITE_CONFIG[key]) {
            return SPRITE_CONFIG[key].frames;
        }
        return fallback;
    }

    function cfgSpeed(key, fallback) {
        if (typeof SPRITE_CONFIG !== "undefined" && SPRITE_CONFIG[key]) {
            return SPRITE_CONFIG[key].speed || fallback;
        }
        return fallback;
    }

    G.cfgFrames = cfgFrames;
    G.cfgSpeed = cfgSpeed;

    // ── Loader ──────────────────────────────────────────────────────────

    function loadImg(key, path) {
        return new Promise(resolve => {
            const img = new Image();
            img.onload = () => { G.sprites[key] = img; resolve(); };
            img.onerror = () => { console.warn("Asset missing:", path); resolve(); };
            img.src = ASSET + "/" + path.split("/").map(s => encodeURIComponent(s)).join("/");
        });
    }

    G.loadAllSprites = async function () {
        await Promise.all([
            // Tilesets
            loadImg("ts_grass", "Terrain/Tileset/Tilemap_color2.png"),
            loadImg("ts_dirt",  "Terrain/Tileset/Tilemap_color4.png"),
            loadImg("ts_sand",  "Terrain/Tileset/Tilemap_color5.png"),
            loadImg("water_bg", "Terrain/Tileset/Water Background color.png"),
            loadImg("water_foam","Terrain/Tileset/Water Foam.png"),

            // Trees
            loadImg("tree1", "Terrain/Resources/Wood/Trees/Tree1.png"),
            loadImg("tree2", "Terrain/Resources/Wood/Trees/Tree2.png"),
            loadImg("tree3", "Terrain/Resources/Wood/Trees/Tree3.png"),
            loadImg("tree4", "Terrain/Resources/Wood/Trees/Tree4.png"),
            loadImg("stump1","Terrain/Resources/Wood/Trees/Stump 1.png"),
            loadImg("stump2","Terrain/Resources/Wood/Trees/Stump 2.png"),
            loadImg("stump3","Terrain/Resources/Wood/Trees/Stump 3.png"),
            loadImg("stump4","Terrain/Resources/Wood/Trees/Stump 4.png"),

            // Rocks
            loadImg("rock1", "Terrain/Decorations/Rocks/Rock1.png"),
            loadImg("rock2", "Terrain/Decorations/Rocks/Rock2.png"),
            loadImg("rock3", "Terrain/Decorations/Rocks/Rock3.png"),
            loadImg("rock4", "Terrain/Decorations/Rocks/Rock4.png"),

            // Gold stones + highlights
            loadImg("gold1", "Terrain/Resources/Gold/Gold Stones/Gold Stone 1.png"),
            loadImg("gold2", "Terrain/Resources/Gold/Gold Stones/Gold Stone 2.png"),
            loadImg("gold3", "Terrain/Resources/Gold/Gold Stones/Gold Stone 3.png"),
            loadImg("gold4", "Terrain/Resources/Gold/Gold Stones/Gold Stone 4.png"),
            loadImg("gold5", "Terrain/Resources/Gold/Gold Stones/Gold Stone 5.png"),
            loadImg("gold6", "Terrain/Resources/Gold/Gold Stones/Gold Stone 6.png"),
            loadImg("gold_hl1", "Terrain/Resources/Gold/Gold Stones/Gold Stone 1_Highlight.png"),
            loadImg("gold_hl2", "Terrain/Resources/Gold/Gold Stones/Gold Stone 2_Highlight.png"),
            loadImg("gold_hl3", "Terrain/Resources/Gold/Gold Stones/Gold Stone 3_Highlight.png"),
            loadImg("gold_hl4", "Terrain/Resources/Gold/Gold Stones/Gold Stone 4_Highlight.png"),
            loadImg("gold_hl5", "Terrain/Resources/Gold/Gold Stones/Gold Stone 5_Highlight.png"),
            loadImg("gold_hl6", "Terrain/Resources/Gold/Gold Stones/Gold Stone 6_Highlight.png"),

            // Bushes
            loadImg("bush1", "Terrain/Decorations/Bushes/Bushe1.png"),
            loadImg("bush2", "Terrain/Decorations/Bushes/Bushe2.png"),
            loadImg("bush3", "Terrain/Decorations/Bushes/Bushe3.png"),
            loadImg("bush4", "Terrain/Decorations/Bushes/Bushe4.png"),

            // Clouds
            loadImg("cloud1", "Terrain/Decorations/Clouds/Clouds_01.png"),
            loadImg("cloud2", "Terrain/Decorations/Clouds/Clouds_02.png"),
            loadImg("cloud3", "Terrain/Decorations/Clouds/Clouds_03.png"),
            loadImg("cloud4", "Terrain/Decorations/Clouds/Clouds_04.png"),
            loadImg("cloud5", "Terrain/Decorations/Clouds/Clouds_05.png"),
            loadImg("cloud6", "Terrain/Decorations/Clouds/Clouds_06.png"),
            loadImg("cloud7", "Terrain/Decorations/Clouds/Clouds_07.png"),
            loadImg("cloud8", "Terrain/Decorations/Clouds/Clouds_08.png"),

            // Water rocks
            loadImg("water_rock1", "Terrain/Decorations/Rocks in the Water/Water Rocks_01.png"),
            loadImg("water_rock2", "Terrain/Decorations/Rocks in the Water/Water Rocks_02.png"),
            loadImg("water_rock3", "Terrain/Decorations/Rocks in the Water/Water Rocks_03.png"),
            loadImg("water_rock4", "Terrain/Decorations/Rocks in the Water/Water Rocks_04.png"),

            // Buildings
            loadImg("house1",    "Buildings/Blue Buildings/House1.png"),
            loadImg("house2",    "Buildings/Blue Buildings/House2.png"),
            loadImg("house3",    "Buildings/Blue Buildings/House3.png"),
            loadImg("castle",    "Buildings/Blue Buildings/Castle.png"),
            loadImg("barracks",  "Buildings/Blue Buildings/Barracks.png"),
            loadImg("tower",     "Buildings/Blue Buildings/Tower.png"),
            loadImg("archery",   "Buildings/Blue Buildings/Archery.png"),
            loadImg("monastery", "Buildings/Blue Buildings/Monastery.png"),

            // Pawn sprites
            loadImg("pawn_idle",      "Units/Blue Units/Pawn/Pawn_Idle.png"),
            loadImg("pawn_run",       "Units/Blue Units/Pawn/Pawn_Run.png"),
            loadImg("pawn_idle_axe",  "Units/Blue Units/Pawn/Pawn_Idle Axe.png"),
            loadImg("pawn_idle_pick", "Units/Blue Units/Pawn/Pawn_Idle Pickaxe.png"),
            loadImg("pawn_idle_ham",  "Units/Blue Units/Pawn/Pawn_Idle Hammer.png"),
            loadImg("pawn_idle_wood", "Units/Blue Units/Pawn/Pawn_Idle Wood.png"),
            loadImg("pawn_idle_gold", "Units/Blue Units/Pawn/Pawn_Idle Gold.png"),
            loadImg("pawn_idle_meat", "Units/Blue Units/Pawn/Pawn_Idle Meat.png"),
            loadImg("pawn_idle_knife","Units/Blue Units/Pawn/Pawn_Idle Knife.png"),
            loadImg("pawn_run_axe",   "Units/Blue Units/Pawn/Pawn_Run Axe.png"),
            loadImg("pawn_run_pick",  "Units/Blue Units/Pawn/Pawn_Run Pickaxe.png"),
            loadImg("pawn_run_ham",   "Units/Blue Units/Pawn/Pawn_Run Hammer.png"),
            loadImg("pawn_run_wood",  "Units/Blue Units/Pawn/Pawn_Run Wood.png"),
            loadImg("pawn_run_gold",  "Units/Blue Units/Pawn/Pawn_Run Gold.png"),
            loadImg("pawn_run_meat",  "Units/Blue Units/Pawn/Pawn_Run Meat.png"),
            loadImg("pawn_act_axe",   "Units/Blue Units/Pawn/Pawn_Interact Axe.png"),
            loadImg("pawn_act_pick",  "Units/Blue Units/Pawn/Pawn_Interact Pickaxe.png"),
            loadImg("pawn_act_ham",   "Units/Blue Units/Pawn/Pawn_Interact Hammer.png"),
            loadImg("pawn_act_knife", "Units/Blue Units/Pawn/Pawn_Interact Knife.png"),

            // Sheep sprites
            loadImg("sheep_idle",  "Terrain/Resources/Meat/Sheep/Sheep_Idle.png"),
            loadImg("sheep_move",  "Terrain/Resources/Meat/Sheep/Sheep_Move.png"),
            loadImg("sheep_grass", "Terrain/Resources/Meat/Sheep/Sheep_Grass.png"),

            // Blue Archer sprites (playable)
            loadImg("archer_idle",  "Units/Blue Units/Archer/Archer_Idle.png"),
            loadImg("archer_run",   "Units/Blue Units/Archer/Archer_Run.png"),
            loadImg("archer_shoot", "Units/Blue Units/Archer/Archer_Shoot.png"),
            loadImg("archer_arrow", "Units/Blue Units/Archer/Arrow.png"),

            // Red Archer sprites (wild / enemy)
            loadImg("red_archer_idle",  "Units/Red Units/Archer/Archer_Idle.png"),
            loadImg("red_archer_run",   "Units/Red Units/Archer/Archer_Run.png"),
            loadImg("red_archer_shoot", "Units/Red Units/Archer/Archer_Shoot.png"),
            loadImg("red_archer_arrow", "Units/Red Units/Archer/Arrow.png"),

            // Le Chat – 27 individual frames
            ...Array.from({ length: 27 }, (_, i) =>
                loadImg("lechat_" + i, "lechat/frame_" + String(i).padStart(3, "0") + ".png")
            ),

            // Particle FX
            loadImg("dust1",  "Particle FX/Dust_01.png"),
            loadImg("dust2",  "Particle FX/Dust_02.png"),
            loadImg("fire1",  "Particle FX/Fire_01.png"),
            loadImg("fire2",  "Particle FX/Fire_02.png"),

            // Shadow
            loadImg("shadow", "Terrain/Tileset/Shadow.png"),
        ]);
        G.spritesLoaded = true;
    };

    // ── Animation helpers ───────────────────────────────────────────────

    G.spriteFrame = function (frames, speed, offset) {
        const interval = ANIM_SPEED[speed] || ANIM_SPEED.normal;
        return (((Math.floor(G.gameFrame / interval) + (offset || 0)) % frames) + frames) % frames;
    };

    G.drawSpriteFrame = function (ctx, img, frameIdx, totalFrames, dx, dy, dw, dh, flip) {
        if (!img) return false;
        const sw = img.width / totalFrames;
        const sh = img.height;
        const srcX = frameIdx * sw;
        ctx.save();
        if (flip) {
            ctx.translate(dx + dw, dy);
            ctx.scale(-1, 1);
            ctx.drawImage(img, srcX, 0, sw, sh, 0, 0, dw, dh);
        } else {
            ctx.drawImage(img, srcX, 0, sw, sh, dx, dy, dw, dh);
        }
        ctx.restore();
        return true;
    };

    /** Deterministic hash from tile position */
    G.posHash = function (c, r, mod) {
        return ((c * 7 + r * 13 + c * r * 3) & 0x7FFFFFFF) % mod;
    };

    /** Track NPC facing direction based on movement */
    G.updateFacing = function (npc) {
        if (!G.npcFacing[npc.id]) G.npcFacing[npc.id] = { lx: npc.x, r: true };
        const f = G.npcFacing[npc.id];
        if (npc.state === "PERFORMING") return f.r;
        if (Math.abs(npc.x - f.lx) > 1.0) f.r = npc.x > f.lx;
        f.lx = npc.x;
        return f.r;
    };

})(window.G4AL);
