/* ═══════════════════════════════════════════════════════════════════════════
   G4AL Web Client – Canvas Renderer + WebSocket + Push-to-Talk
   ═══════════════════════════════════════════════════════════════════════════ */

(() => {
    "use strict";

    // ── Constants ───────────────────────────────────────────────────────────
    const CAMERA_SPEED = 10;        // px per frame when scrolling
    const API = "";                  // same origin

    // ── Tile colors (fallback when sprites not loaded) ──────────────────────
    const TILE_COLORS = {
        0: { light: "#7cb342", dark: "#689f38" },   // GRASS
        1: { light: "#a18864", dark: "#a18864" },   // DIRT
        2: { light: "#dcc88c", dark: "#dcc88c" },   // SAND
        3: { light: "#42a5f5", dark: "#42a5f5" },   // WATER
    };

    // ═══════════════════════════════════════════════════════════════════════════
    //  Sprite Loading System
    // ═══════════════════════════════════════════════════════════════════════════

    const ASSET = "/static/assets";
    const sprites = {};
    let spritesLoaded = false;
    let decorations = [];
    const npcFacing = {};

    function loadImg(key, path) {
        return new Promise(resolve => {
            const img = new Image();
            img.onload = () => { sprites[key] = img; resolve(); };
            img.onerror = () => { console.warn("Asset missing:", path); resolve(); };
            img.src = ASSET + "/" + path.split("/").map(s => encodeURIComponent(s)).join("/");
        });
    }

    (async function loadAllSprites() {
        await Promise.all([
            // Tilesets (different color palettes for different terrain types)
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

            // Rocks
            loadImg("rock1", "Terrain/Decorations/Rocks/Rock1.png"),
            loadImg("rock2", "Terrain/Decorations/Rocks/Rock2.png"),
            loadImg("rock3", "Terrain/Decorations/Rocks/Rock3.png"),
            loadImg("rock4", "Terrain/Decorations/Rocks/Rock4.png"),

            // Gold stones
            loadImg("gold1", "Terrain/Resources/Gold/Gold Stones/Gold Stone 1.png"),
            loadImg("gold2", "Terrain/Resources/Gold/Gold Stones/Gold Stone 2.png"),
            loadImg("gold3", "Terrain/Resources/Gold/Gold Stones/Gold Stone 3.png"),

            // Bushes (decorative)
            loadImg("bush1", "Terrain/Decorations/Bushes/Bushe1.png"),
            loadImg("bush2", "Terrain/Decorations/Bushes/Bushe2.png"),
            loadImg("bush3", "Terrain/Decorations/Bushes/Bushe3.png"),
            loadImg("bush4", "Terrain/Decorations/Bushes/Bushe4.png"),

            // Buildings
            loadImg("house1", "Buildings/Blue Buildings/House1.png"),
            loadImg("house2", "Buildings/Blue Buildings/House2.png"),
            loadImg("house3", "Buildings/Blue Buildings/House3.png"),
            loadImg("castle", "Buildings/Blue Buildings/Castle.png"),

            // Pawn sprites (Blue)
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

            // Shadow
            loadImg("shadow", "Terrain/Tileset/Shadow.png"),
        ]);
        spritesLoaded = true;
        // Rebuild map with sprite tiles if map data already arrived
        if (mapCached) buildMapImage();
    })();

    // ── Animation System ────────────────────────────────────────────────────

    let gameFrame = 0; // incremented every render()

    // Speed tiers: game frames per animation frame change
    const ANIM_SPEED = { slow: 30, normal: 12, fast: 5 };

    /**
     * Compute the current animation frame index.
     * @param {number} frames   Total frames in the sprite sheet
     * @param {string} speed    'slow' | 'normal' | 'fast'
     * @param {number} [offset] Per-instance offset for desync (e.g. wind)
     */
    function spriteFrame(frames, speed, offset) {
        const interval = ANIM_SPEED[speed] || ANIM_SPEED.normal;
        return (((Math.floor(gameFrame / interval) + (offset || 0)) % frames) + frames) % frames;
    }

    /**
     * Draw one frame from a horizontal sprite sheet.
     * sWidth is computed as img.width / totalFrames – no hardcoded values.
     */
    function drawSpriteFrame(ctx, img, frameIdx, totalFrames, dx, dy, dw, dh, flip) {
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
    }

    /** Deterministic hash from tile position – for stable random variations */
    function posHash(c, r, mod) {
        return ((c * 7 + r * 13 + c * r * 3) & 0x7FFFFFFF) % mod;
    }

    /** Track NPC facing direction based on movement */
    function updateFacing(npc) {
        if (!npcFacing[npc.id]) npcFacing[npc.id] = { lx: npc.x, r: true };
        const f = npcFacing[npc.id];
        if (Math.abs(npc.x - f.lx) > 0.3) f.r = npc.x > f.lx;
        f.lx = npc.x;
        return f.r;
    }

    // ── State ───────────────────────────────────────────────────────────
    let gameState = null;       // latest from server
    let mapCached = null;       // {cols, rows, tileSize, tiles} – only changes on load
    let selectedId = null;       // currently selected NPC id

    // Camera
    let camX = 0, camY = 0;
    let cameraCentered = false;
    const keysDown = new Set();


    // Canvas refs
    const canvas = document.getElementById("game-canvas");
    const ctx = canvas.getContext("2d");
    const container = document.getElementById("canvas-container");

    // ── Socket.IO connection ─────────────────────────────────────────────
    const socket = io();
    socket.on("state", (data) => {
        gameState = data;
        // Cache map on first state
        if (!mapCached && gameState.map) {
            mapCached = gameState.map;
            buildMapImage();
        }
        // Center camera on first NPC once
        if (!cameraCentered && mapCached && gameState.npcs && gameState.npcs.length > 0) {
            const npc = gameState.npcs[0];
            const W = canvas.width  || container.clientWidth;
            const H = canvas.height || container.clientHeight;
            const maxX = mapCached.cols * mapCached.tileSize - W;
            const maxY = mapCached.rows * mapCached.tileSize - H;
            camX = Math.max(0, Math.min(npc.x - W / 2, maxX));
            camY = Math.max(0, Math.min(npc.y - H / 2, maxY));
            cameraCentered = true;
        }
    });

    // ── Resize canvas to fill container ─────────────────────────────────────
    function resizeCanvas() {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    // ── REST helper (still used for actions/commands) ────────────────────────
    async function postJSON(endpoint, body) {
        try {
            await fetch(`${API}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
        } catch (e) { console.error(e); }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Push-to-Talk (hold G) – Web Audio API
    // ═══════════════════════════════════════════════════════════════════════════

    let pttRecording = false;
    let pttMediaStream = null;
    let pttRecorder = null;
    let pttChunks = [];

    /** Show a visual indicator that we're recording */
    function setPttIndicator(active) {
        let el = document.getElementById("ptt-indicator");
        if (!el) {
            el = document.createElement("div");
            el.id = "ptt-indicator";
            el.textContent = "\ud83c\udfa4 Recording\u2026";
            el.style.cssText = `
            position:fixed; top:12px; left:50%; transform:translateX(-50%);
            background:#e53935; color:#fff; padding:6px 18px; border-radius:20px;
            font-weight:bold; font-size:14px; z-index:9999;
            box-shadow:0 2px 8px rgba(0,0,0,0.4); display:none;
        `;
            document.body.appendChild(el);
        }
        el.style.display = active ? "block" : "none";
    }

    async function pttStart() {
        if (pttRecording) return;
        pttRecording = true;
        pttChunks = [];
        setPttIndicator(true);

        try {
            pttMediaStream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
            });

            // Prefer WAV-like format; fall back to webm
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "";
            pttRecorder = new MediaRecorder(pttMediaStream, mimeType ? { mimeType } : {});

            pttRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) pttChunks.push(e.data);
            };

            pttRecorder.onstop = async () => {
                setPttIndicator(false);
                // Stop mic tracks
                pttMediaStream.getTracks().forEach(t => t.stop());

                if (pttChunks.length === 0) return;

                const blob = new Blob(pttChunks, { type: pttRecorder.mimeType });
                // Convert to WAV via AudioContext for consistent format
                const wavBlob = await blobToWav(blob);

                // Send to server
                const form = new FormData();
                form.append("audio", wavBlob, "recording.wav");
                try {
                    await fetch(`${API}/api/audio`, { method: "POST", body: form });
                } catch (e) { console.error("PTT upload failed:", e); }
            };

            pttRecorder.start();
        } catch (e) {
            console.error("Mic access denied or unavailable:", e);
            pttRecording = false;
            setPttIndicator(false);
        }
    }

    function pttStop() {
        if (!pttRecording || !pttRecorder) return;
        pttRecording = false;
        if (pttRecorder.state === "recording") {
            pttRecorder.stop();
        }
    }

    /**
     * Convert an audio Blob (webm/ogg/etc) to 16-bit PCM WAV via AudioContext.
     * This gives the Voxtral API a clean WAV regardless of browser codec.
     */
    async function blobToWav(blob) {
        const arrayBuf = await blob.arrayBuffer();
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        let audioBuf;
        try {
            audioBuf = await audioCtx.decodeAudioData(arrayBuf);
        } catch {
            // If decoding fails (rare), just send the raw blob
            audioCtx.close();
            return blob;
        }
        audioCtx.close();

        // Downmix to mono
        const samples = audioBuf.getChannelData(0);
        const numSamples = samples.length;

        // Build WAV
        const buffer = new ArrayBuffer(44 + numSamples * 2);
        const view = new DataView(buffer);

        function writeStr(offset, str) {
            for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
        }
        writeStr(0, "RIFF");
        view.setUint32(4, 36 + numSamples * 2, true);
        writeStr(8, "WAVE");
        writeStr(12, "fmt ");
        view.setUint32(16, 16, true);          // chunk size
        view.setUint16(20, 1, true);           // PCM
        view.setUint16(22, 1, true);           // mono
        view.setUint32(24, 16000, true);       // sample rate
        view.setUint32(28, 32000, true);       // byte rate
        view.setUint16(32, 2, true);           // block align
        view.setUint16(34, 16, true);          // bits per sample
        writeStr(36, "data");
        view.setUint32(40, numSamples * 2, true);

        // Float32 → Int16
        let offset = 44;
        for (let i = 0; i < numSamples; i++) {
            let s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            offset += 2;
        }

        return new Blob([buffer], { type: "audio/wav" });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Map rendering (pre-rendered to offscreen canvas with tileset sprites)
    // ═══════════════════════════════════════════════════════════════════════════

    let mapCanvas = null;

    /*  Tiny Swords tileset layout (576×384, 9×6 grid of 64×64 tiles):
     *  The tileset is organized as TWO 3×3 auto-tile groups side-by-side,
     *  with extra edge/transition pieces. Only the FIRST group rows 0-2
     *  are guaranteed to contain full filled tiles.
     *
     *  Group 1 (cols 0-2):
     *    (0,0)=inner-corner-TL  (1,0)=top-edge   (2,0)=inner-corner-TR
     *    (0,1)=left-edge        (1,1)=CENTER/FILL (2,1)=right-edge
     *    (0,2)=inner-corner-BL  (1,2)=bot-edge    (2,2)=inner-corner-BR
     *
     *  Only (1,1) is always a pure filled tile. The corners (0,0),(2,0),
     *  (0,2),(2,2) are often also filled variants but may have inner
     *  corner dithering. Positions beyond col 2 or row 2 may be empty
     *  or edge-only, which is what caused the black diagonal tiles.
     *
     *  FIX: use only (1,1) and add subtle brightness variation.
     */

    function buildMapImage() {
        if (!mapCached) return;
        const { cols, rows, tileSize, tiles } = mapCached;
        mapCanvas = document.createElement("canvas");
        mapCanvas.width = cols * tileSize;
        mapCanvas.height = rows * tileSize;
        const mctx = mapCanvas.getContext("2d");
        decorations = [];

        // Source tile: always the center (1,1) of the first auto-tile group
        const SRC_X = 1 * 64;
        const SRC_Y = 1 * 64;

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const tt = tiles[r][c];
                const px = c * tileSize;
                const py = r * tileSize;

                let tileset = null;
                if (tt === 0) tileset = sprites.ts_grass;
                else if (tt === 1) tileset = sprites.ts_dirt;
                else if (tt === 2) tileset = sprites.ts_sand;
                else if (tt === 3) {
                    // Water tile
                    if (sprites.water_bg) {
                        mctx.drawImage(sprites.water_bg, px, py, tileSize, tileSize);
                    } else {
                        mctx.fillStyle = "#42a5f5";
                        mctx.fillRect(px, py, tileSize, tileSize);
                    }
                    continue;
                }

                if (tileset) {
                    // Draw the center tile from the tileset
                    mctx.drawImage(tileset, SRC_X, SRC_Y, 64, 64, px, py, tileSize, tileSize);

                    // Subtle checkerboard brightness variation for visual interest
                    if ((r + c) % 2 === 0) {
                        mctx.fillStyle = "rgba(0,0,0,0.04)";
                        mctx.fillRect(px, py, tileSize, tileSize);
                    }
                } else {
                    // Fallback: colored tiles
                    const colors = TILE_COLORS[tt] || TILE_COLORS[0];
                    const color = (r + c) % 2 === 0 ? colors.light : colors.dark;
                    mctx.fillStyle = color;
                    mctx.fillRect(px, py, tileSize, tileSize);
                }

                // Random decorative bushes on grass tiles (~3% chance, deterministic)
                if (tt === 0 && posHash(c + 1, r + 3, 30) === 0) {
                    decorations.push({
                        type: "bush",
                        variant: posHash(c, r, 4) + 1,
                        offset: posHash(c + r, r * c, 8), // desync wind animation
                        x: px + tileSize / 2,
                        y: py + tileSize / 2,
                    });
                }
            }
        }
    }

    function darken(hex, amount) {
        const r = Math.max(0, parseInt(hex.slice(1, 3), 16) - amount);
        const g = Math.max(0, parseInt(hex.slice(3, 5), 16) - amount);
        const b = Math.max(0, parseInt(hex.slice(5, 7), 16) - amount);
        return `rgb(${r},${g},${b})`;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Rendering
    // ═══════════════════════════════════════════════════════════════════════════

    function render() {
        if (!gameState || !mapCached) {
            requestAnimationFrame(render);
            return;
        }

        const W = canvas.width;
        const H = canvas.height;
        ctx.clearRect(0, 0, W, H);
        gameFrame++;

        // ── Camera update ───────────────────────────────────────────────
        updateCamera(W, H);

        // ── Map ─────────────────────────────────────────────────────────
        if (mapCanvas) {
            ctx.drawImage(mapCanvas, -camX, -camY);
        }

        // ── Water foam animation overlay ────────────────────────────────
        if (sprites.water_foam && mapCached) {
            const ts = mapCached.tileSize;
            const foamFrame = spriteFrame(16, "slow", 0);
            for (let r = 0; r < mapCached.rows; r++) {
                for (let c = 0; c < mapCached.cols; c++) {
                    if (mapCached.tiles[r][c] !== 3) continue;
                    const wx = c * ts - camX;
                    const wy = r * ts - camY;
                    if (wx < -ts || wx > W + ts || wy < -ts || wy > H + ts) continue;
                    ctx.globalAlpha = 0.3;
                    drawSpriteFrame(ctx, sprites.water_foam, foamFrame, 16, wx, wy, ts, ts, false);
                    ctx.globalAlpha = 1;
                }
            }
        }

        // ── Decorations (bushes – animated wind) ────────────────────────
        for (const deco of decorations) {
            const dx = deco.x - camX;
            const dy = deco.y - camY;
            if (dx < -64 || dx > W + 64 || dy < -64 || dy > H + 64) continue;
            const bushSpr = sprites["bush" + deco.variant];
            if (bushSpr) {
                const sz = 30;
                const fi = spriteFrame(8, "slow", deco.offset);
                drawSpriteFrame(ctx, bushSpr, fi, 8,
                    dx - sz / 2, dy - sz / 2, sz, sz, false);
            }
        }

        // ── Resources ───────────────────────────────────────────────────
        const ts = mapCached.tileSize;
        for (const res of gameState.resources) {
            const sx = res.col * ts + ts / 2 - camX;
            const sy = res.row * ts + ts / 2 - camY;

            // Cull off-screen (expanded for large sprites)
            if (sx < -ts * 2 || sx > W + ts * 2 || sy < -ts * 2 || sy > H + ts * 2) continue;

            drawResource(ctx, res, sx, sy, ts);
        }

        // ── NPCs (sorted by y for depth) ────────────────────────────────
        const npcs = [...gameState.npcs].sort((a, b) => a.y - b.y);
        for (const npc of npcs) {
            const sx = npc.x - camX;
            const sy = npc.y - camY;
            if (sx < -80 || sx > W + 80 || sy < -80 || sy > H + 80) continue;
            drawNPC(ctx, npc, sx, sy);
        }

        // ── UI overlay updates ──────────────────────────────────────────
        updateUI();
        updateSpeechBubbles();

        requestAnimationFrame(render);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Draw resource (sprite-based with fallbacks)
    // ═══════════════════════════════════════════════════════════════════════════

    function drawResource(ctx, res, sx, sy, ts) {
        switch (res.kind) {
            case "tree": {
                const v = posHash(res.col, res.row, 4) + 1;
                const spr = sprites["tree" + v];
                if (spr) {
                    // Tree sprite: 8 frames wind animation (1536×256 → 192×256 per frame)
                    const offset = posHash(res.col, res.row, 8); // desync wind
                    const frame = spriteFrame(8, "slow", offset);
                    const dw = ts * 2.0;
                    const dh = ts * 2.6;
                    drawSpriteFrame(ctx, spr, frame, 8,
                        sx - dw / 2, sy - dh + ts * 0.5, dw, dh, false);
                } else {
                    // Fallback: simple shapes
                    ctx.fillStyle = "#795b3d";
                    ctx.fillRect(sx - 4, sy - 2, 8, 16);
                    ctx.fillStyle = "#388e3c";
                    ctx.beginPath();
                    ctx.arc(sx, sy - 10, 18, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = "#4caf50";
                    ctx.beginPath();
                    ctx.arc(sx - 3, sy - 14, 13, 0, Math.PI * 2);
                    ctx.fill();
                }
                break;
            }

            case "rock": {
                if (res.hasGold) {
                    const v = posHash(res.col, res.row, 3) + 1;
                    const spr = sprites["gold" + v];
                    if (spr) {
                        const sz = ts * 1.0;
                        ctx.drawImage(spr, sx - sz / 2, sy - sz / 2, sz, sz);
                    } else {
                        ctx.fillStyle = "#9e9e9e";
                        ctx.beginPath();
                        ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.fillStyle = "#ffd700";
                        [[-5, -2], [3, 1], [-1, 4]].forEach(([dx, dy]) => {
                            ctx.beginPath();
                            ctx.arc(sx + dx, sy + dy, 2.5, 0, Math.PI * 2);
                            ctx.fill();
                        });
                    }
                } else {
                    const v = posHash(res.col, res.row, 4) + 1;
                    const spr = sprites["rock" + v];
                    if (spr) {
                        const sz = ts * 0.8;
                        ctx.drawImage(spr, sx - sz / 2, sy - sz / 2, sz, sz);
                    } else {
                        ctx.fillStyle = "#757575";
                        ctx.beginPath();
                        ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2);
                        ctx.fill();
                    }
                }
                break;
            }

            case "structure": {
                const houseKey = "house" + (posHash(res.col, res.row, 3) + 1);
                const houseSpr = sprites[houseKey] || sprites.house1;
                if (res.built) {
                    if (houseSpr) {
                        // House1=128×192 → draw ~2 tiles wide, ~3 tiles tall
                        const dw = ts * 2;
                        const dh = ts * 3;
                        ctx.drawImage(houseSpr, sx - dw / 2, sy - dh + ts * 0.6, dw, dh);
                    } else {
                        ctx.fillStyle = "#654321";
                        ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#503018";
                        ctx.lineWidth = 2;
                        ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                        ctx.fillStyle = "#b22222";
                        ctx.beginPath();
                        ctx.moveTo(sx - 24, sy - 20);
                        ctx.lineTo(sx + 24, sy - 20);
                        ctx.lineTo(sx, sy - 38);
                        ctx.closePath();
                        ctx.fill();
                    }
                } else {
                    // Under construction → semi-transparent + progress bar
                    if (houseSpr) {
                        ctx.globalAlpha = 0.2 + 0.8 * (res.buildProgress / 100);
                        const dw = ts * 2;
                        const dh = ts * 3;
                        ctx.drawImage(houseSpr, sx - dw / 2, sy - dh + ts * 0.6, dw, dh);
                        ctx.globalAlpha = 1;
                    } else {
                        ctx.fillStyle = "#8b7765";
                        ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#50403c";
                        ctx.lineWidth = 2;
                        ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                    }
                    drawBar(ctx, sx, sy - ts - 10, 36, 5, res.buildProgress / 100, "#4caf50");
                }
                break;
            }

            case "wheat": {
                const half = ts / 2 - 4;

                // Ground patch
                ctx.fillStyle = "#8b7750";
                roundRect(ctx, sx - half, sy - half + 4, half * 2, half * 2 - 4, 4);
                ctx.fill();

                // Stalks
                const stalkH = 6 + 20 * res.growthRatio;
                const r_val = Math.floor(80 + 175 * res.growthRatio);
                const g_val = Math.floor(100 + 155 * res.growthRatio);
                ctx.strokeStyle = `rgb(${r_val},${g_val},30)`;
                ctx.lineWidth = 2;
                for (let dx = -half + 4; dx < half; dx += 6) {
                    const bx = sx + dx;
                    const by = sy + half - 2;
                    ctx.beginPath();
                    ctx.moveTo(bx, by);
                    ctx.lineTo(bx, by - stalkH);
                    ctx.stroke();
                    if (res.growthRatio > 0.6) {
                        ctx.fillStyle = "#dac350";
                        ctx.beginPath();
                        ctx.arc(bx, by - stalkH, 3, 0, Math.PI * 2);
                        ctx.fill();
                    }
                }

                // Growth / Ready indicator
                if (!res.fullyGrown) {
                    drawBar(ctx, sx, sy - half - 6, 30, 5, res.growthRatio, "#4caf50");
                } else {
                    ctx.fillStyle = "#ffe650";
                    ctx.font = "bold 11px Consolas";
                    ctx.textAlign = "center";
                    ctx.fillText("READY", sx, sy - half - 4);
                }
                break;
            }
        }

        // HP bar for damaged resource
        if (res.hp < res.maxHp && res.kind !== "wheat" && res.kind !== "structure") {
            drawBar(ctx, sx, sy - ts / 2 - 8, 30, 5, res.hp / res.maxHp, "#4caf50");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Draw NPC (animated sprite-based with fallback)
    // ═══════════════════════════════════════════════════════════════════════════

    /** Pick the right sprite sheet + frame count + speed based on NPC state & action */
    function getNpcSprite(npc) {
        const st = npc.state;
        const act = npc.actionType || "";

        if (st === "MOVING") {
            return { spr: sprites.pawn_run, frames: 6, speed: "fast" };
        }

        if (st === "PERFORMING") {
            switch (act) {
                case "chop_wood":
                    return { spr: sprites.pawn_act_axe,   frames: 6, speed: "fast" };
                case "mine_rock":
                    return { spr: sprites.pawn_act_pick,  frames: 6, speed: "fast" };
                case "build":
                    return { spr: sprites.pawn_act_ham,   frames: 6, speed: "fast" };
                case "plant_wheat":
                case "collect_wheat":
                    return { spr: sprites.pawn_act_knife, frames: 6, speed: "fast" };
                case "eat":
                    return { spr: sprites.pawn_idle_meat, frames: 8, speed: "normal" };
                default:
                    return { spr: sprites.pawn_idle, frames: 8, speed: "normal" };
            }
        }

        // IDLE, DONE, etc.
        return { spr: sprites.pawn_idle, frames: 8, speed: "normal" };
    }

    function drawNPC(ctx, npc, sx, sy) {
        const SIZE = 64;
        const HALF = SIZE / 2;
        const facingRight = updateFacing(npc);

        // Shadow
        if (sprites.shadow) {
            ctx.globalAlpha = 0.25;
            ctx.drawImage(sprites.shadow, 0, 0, 192, 192,
                sx - HALF * 0.7, sy - 4, SIZE * 0.7, SIZE * 0.35);
            ctx.globalAlpha = 1;
        } else {
            ctx.fillStyle = "rgba(0,0,0,0.25)";
            ctx.beginPath();
            ctx.ellipse(sx, sy, HALF * 0.6, HALF * 0.25, 0, 0, Math.PI * 2);
            ctx.fill();
        }

        // Selection ring
        if (npc.selected) {
            ctx.strokeStyle = "#00e676";
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.ellipse(sx, sy + 2, HALF + 4, HALF * 0.35 + 2, 0, 0, Math.PI * 2);
            ctx.stroke();
        }

        // Sprite
        const info = getNpcSprite(npc);
        const frame = spriteFrame(info.frames, info.speed, npc.id);
        const spriteDrawn = info.spr && drawSpriteFrame(ctx, info.spr, frame, info.frames,
            sx - HALF, sy - SIZE + 10, SIZE, SIZE, !facingRight);

        if (!spriteDrawn) {
            // Fallback: colored circle
            const bob = npc.state === "IDLE" ? Math.sin(Date.now() / 200) * 2 : 0;
            const by = sy + bob;
            ctx.fillStyle = "#ffb74d";
            ctx.beginPath();
            ctx.arc(sx, by - 14, 14, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = npc.selected ? "#00e676" : "#e6801e";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(sx, by - 14, 14, 0, Math.PI * 2);
            ctx.stroke();
            // Eyes
            ctx.fillStyle = "#333";
            ctx.beginPath();
            ctx.arc(sx - 4, by - 17, 2, 0, Math.PI * 2);
            ctx.arc(sx + 4, by - 17, 2, 0, Math.PI * 2);
            ctx.fill();
        }

        // Name label
        ctx.font = "bold 11px Consolas";
        ctx.textAlign = "center";
        ctx.fillStyle = "rgba(0,0,0,0.7)";
        ctx.fillText(npc.name, sx + 1, sy - SIZE + 4);
        ctx.fillStyle = "#fff";
        ctx.fillText(npc.name, sx, sy - SIZE + 3);

        // State label
        ctx.font = "9px Consolas";
        ctx.fillStyle = "#ddd";
        ctx.fillText(npc.state, sx, sy - SIZE + 14);

        // HP bar (only when damaged)
        if (npc.health < npc.maxHealth) {
            drawBar(ctx, sx, sy - SIZE - 2, 28, 4, npc.health / npc.maxHealth, "#4caf50");
        }

        // Hunger bar (always visible)
        const hungerRatio = npc.hunger / npc.maxHunger;
        const hungerColor = hungerRatio > 0.25 ? "#ff9800" : "#f44336";
        drawBar(ctx, sx, sy + 8, 24, 4, hungerRatio, hungerColor);
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    function drawBar(ctx, cx, top, w, h, ratio, color) {
        const x = cx - w / 2;
        ctx.fillStyle = "#3c3c3c";
        ctx.fillRect(x, top, w, h);
        if (ratio > 0) {
            ctx.fillStyle = color;
            ctx.fillRect(x, top, w * Math.max(0, Math.min(1, ratio)), h);
        }
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Camera
    // ═══════════════════════════════════════════════════════════════════════════

    function updateCamera(W, H) {
        if (!mapCached) return;
        const maxX = mapCached.cols * mapCached.tileSize - W;
        const maxY = mapCached.rows * mapCached.tileSize - H;

        if (keysDown.has("ArrowLeft") || keysDown.has("a")) camX -= CAMERA_SPEED;
        if (keysDown.has("ArrowRight") || keysDown.has("d")) camX += CAMERA_SPEED;
        if (keysDown.has("ArrowUp") || keysDown.has("w")) camY -= CAMERA_SPEED;
        if (keysDown.has("ArrowDown") || keysDown.has("s")) camY += CAMERA_SPEED;

        camX = Math.max(0, Math.min(camX, maxX));
        camY = Math.max(0, Math.min(camY, maxY));
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  UI Updates (DOM)
    // ═══════════════════════════════════════════════════════════════════════════

    function updateUI() {
        if (!gameState) return;

        // Resources
        document.getElementById("res-wood").textContent = gameState.storage.wood || 0;
        document.getElementById("res-stone").textContent = gameState.storage.stone || 0;
        document.getElementById("res-gold").textContent = gameState.storage.gold || 0;
        document.getElementById("res-wheat").textContent = gameState.storage.wheat || 0;

        // Selection panel
        const sel = gameState.npcs.find(n => n.id === selectedId);
        const unitSection = document.getElementById("unit-select-section");
        if (sel) {
            unitSection.style.display = "block";
            document.getElementById("sel-name").textContent = sel.name;
            document.getElementById("sel-hp-text").textContent = `${Math.round(sel.health)}/${sel.maxHealth}`;
            document.getElementById("sel-hp-bar").style.width = `${(sel.health / sel.maxHealth) * 100}%`;
            document.getElementById("sel-hunger-text").textContent = `${Math.round(sel.hunger)}%`;
            const hungerBar = document.getElementById("sel-hunger-bar");
            hungerBar.style.width = `${(sel.hunger / sel.maxHunger) * 100}%`;
            hungerBar.classList.toggle("low", sel.hunger / sel.maxHunger < 0.25);
            document.getElementById("sel-state").textContent = sel.state;
        } else {
            unitSection.style.display = "none";
        }

        // Action buttons
        document.querySelectorAll(".action-btn").forEach(btn => {
            btn.disabled = !selectedId;
        });

        // Roster
        const rosterEl = document.getElementById("roster-list");
        const rosterHTML = gameState.npcs.map(n => {
            const cls = n.selected ? "roster-entry selected" : "roster-entry";
            const marker = n.selected ? "\u25b8 " : "  ";
            return `<div class="${cls}" data-npc-id="${n.id}">${marker}${n.name}<span class="state-badge">${n.state}</span></div>`;
        }).join("");
        if (rosterEl.innerHTML !== rosterHTML) rosterEl.innerHTML = rosterHTML;

        // Log
        const logEl = document.getElementById("log-messages");
        const logHTML = gameState.log.map(m => `<div class="log-entry">${escapeHtml(m)}</div>`).join("");
        if (logEl.dataset.last !== logHTML) {
            logEl.innerHTML = logHTML;
            logEl.scrollTop = logEl.scrollHeight;
            logEl.dataset.last = logHTML;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Speech Bubbles ──────────────────────────────────────────────────────

    function updateSpeechBubbles() {
        const container = document.getElementById("canvas-container");

        // Remove stale bubbles
        container.querySelectorAll(".speech-bubble").forEach(el => el.remove());

        if (!gameState) return;
        for (const npc of gameState.npcs) {
            if (!npc.speechText) continue;
            const sx = npc.x - camX;
            const sy = npc.y - camY - 70;
            if (sx < -100 || sx > canvas.width + 100 || sy < -100) continue;

            const bubble = document.createElement("div");
            bubble.className = "speech-bubble";
            bubble.textContent = npc.speechText;
            bubble.style.left = sx + "px";
            bubble.style.top = sy + "px";
            container.appendChild(bubble);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Input handling
    // ═══════════════════════════════════════════════════════════════════════════

    // Keyboard (camera scrolling + push-to-talk)
    document.addEventListener("keydown", e => {
        keysDown.add(e.key);

        // G key = push-to-talk
        if ((e.key === "g" || e.key === "G") && !e.repeat) {
            pttStart();
        }
    });
    document.addEventListener("keyup", e => {
        keysDown.delete(e.key);
        if (e.key === "g" || e.key === "G") {
            pttStop();
        }
    });

    // Left click → select NPC
    canvas.addEventListener("click", e => {
        if (!gameState || !mapCached) return;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const wx = mx + camX;
        const wy = my + camY;

        // Try to click on an NPC (expanded hit area for sprites)
        let clicked = null;
        for (const npc of gameState.npcs) {
            const dx = wx - npc.x;
            const dy = wy - npc.y;
            if (Math.sqrt(dx * dx + dy * dy) <= 30) {
                clicked = npc;
                break;
            }
        }

        if (clicked) {
            selectedId = clicked.id;
            postJSON("/api/select", { npcId: clicked.id });
        } else {
            selectedId = null;
            postJSON("/api/select", {});
        }
    });

    // Right click → move selected NPC
    canvas.addEventListener("contextmenu", e => {
        e.preventDefault();
        if (!selectedId || !mapCached) return;
        const rect = canvas.getBoundingClientRect();
        const wx = (e.clientX - rect.left) + camX;
        const wy = (e.clientY - rect.top) + camY;
        const col = Math.floor(wx / mapCached.tileSize);
        const row = Math.floor(wy / mapCached.tileSize);
        postJSON("/api/move", { npcId: selectedId, col, row });
    });

    // Roster click → select NPC
    document.getElementById("roster-list").addEventListener("click", e => {
        const entry = e.target.closest("[data-npc-id]");
        if (!entry) return;
        const id = parseInt(entry.dataset.npcId);
        selectedId = id;
        postJSON("/api/select", { npcId: id });
    });

    // Action buttons
    document.getElementById("action-buttons").addEventListener("click", e => {
        const btn = e.target.closest(".action-btn");
        if (!btn || !selectedId) return;
        const action = btn.dataset.action;
        postJSON("/api/action", { npcId: selectedId, action });
    });

    // ═══════════════════════════════════════════════════════════════════════════
    //  Boot
    // ═══════════════════════════════════════════════════════════════════════════

    // ═══════════════════════════════════════════════════════════════════════════
    //  Mic Permission Modal
    // ═══════════════════════════════════════════════════════════════════════════

    const micModal = document.getElementById("mic-modal");
    const micBtn = document.getElementById("mic-allow-btn");
    const micCloseBtn = document.getElementById("mic-close-btn");

    if (micModal && micBtn) {
        micBtn.addEventListener("click", async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // Stop tracks immediately – we just needed permission
                stream.getTracks().forEach(t => t.stop());
                micBtn.textContent = "[MIC AUTHORIZED]";
                micBtn.classList.add("granted");
                // Dismiss modal after a short delay
                setTimeout(() => {
                    micModal.classList.add("hidden");
                }, 600);
            } catch (err) {
                console.warn("Mic permission denied:", err);
                micBtn.textContent = "[ACCESS DENIED – RETRY]";
            }
        });

        if (micCloseBtn) {
            micCloseBtn.addEventListener("click", () => {
                micModal.classList.add("hidden");
            });
        }

        // Close modal if clicking outside the box
        micModal.addEventListener("click", (e) => {
            if (e.target === micModal) {
                micModal.classList.add("hidden");
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  Team Information Modal
    // ═══════════════════════════════════════════════════════════════════════════

    const teamModal = document.getElementById("team-modal");
    const teamBtn = document.getElementById("g4al-logo-btn");
    const teamCloseBtn = document.getElementById("team-close-btn");

    if (teamModal && teamBtn && teamCloseBtn) {
        teamBtn.addEventListener("click", () => {
            teamModal.classList.remove("hidden");
        });

        teamCloseBtn.addEventListener("click", () => {
            teamModal.classList.add("hidden");
        });

        // Close modal if clicking outside the box
        teamModal.addEventListener("click", (e) => {
            if (e.target === teamModal) {
                teamModal.classList.add("hidden");
            }
        });
    }

    //  Guide Modal (page-turning help)
    // ═══════════════════════════════════════════════════════════════════════════

    const guideModal = document.getElementById("guide-modal");
    const guideOpenBtn = document.getElementById("guide-btn");
    const guideCloseBtn = document.getElementById("guide-close-btn");
    const guidePrev = document.getElementById("guide-prev");
    const guideNext = document.getElementById("guide-next");
    const guidePageNum = document.getElementById("guide-page-num");
    const guidePages = document.querySelectorAll(".guide-page");
    const totalPages = guidePages.length;
    let currentGuidePage = 1;

    function showGuidePage(n) {
        currentGuidePage = Math.max(1, Math.min(n, totalPages));
        guidePages.forEach(p => p.classList.remove("active"));
        const target = document.querySelector(`.guide-page[data-page="${currentGuidePage}"]`);
        if (target) target.classList.add("active");
        guidePageNum.textContent = `${currentGuidePage} / ${totalPages}`;
        guidePrev.disabled = currentGuidePage === 1;
        guideNext.disabled = currentGuidePage === totalPages;
    }

    if (guideModal && guideOpenBtn) {
        guideOpenBtn.addEventListener("click", () => {
            showGuidePage(1);
            guideModal.classList.remove("hidden");
        });

        guideCloseBtn.addEventListener("click", () => {
            guideModal.classList.add("hidden");
        });

        guidePrev.addEventListener("click", () => showGuidePage(currentGuidePage - 1));
        guideNext.addEventListener("click", () => showGuidePage(currentGuidePage + 1));

        guideModal.addEventListener("click", (e) => {
            if (e.target === guideModal) guideModal.classList.add("hidden");
        });

        document.addEventListener("keydown", (e) => {
            if (guideModal.classList.contains("hidden")) return;
            if (e.key === "Escape") guideModal.classList.add("hidden");
            if (e.key === "ArrowLeft") showGuidePage(currentGuidePage - 1);
            if (e.key === "ArrowRight") showGuidePage(currentGuidePage + 1);
        });
    }

    // Start render loop (state arrives via WebSocket)
    requestAnimationFrame(render);

})();
