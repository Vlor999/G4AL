/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Map Building, Rendering Loop, Resource & NPC Drawing
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    const TILE_COLORS = {
        0: { light: "#7cb342", dark: "#689f38" },
        1: { light: "#a18864", dark: "#a18864" },
        2: { light: "#dcc88c", dark: "#dcc88c" },
        3: { light: "#42a5f5", dark: "#42a5f5" },
    };

    // Map state
    let mapCanvas = null;
    let decorations = [];
    let clouds = [];
    let waterRocks = [];
    const particles = [];

    G.decorations = decorations;
    G.particles = particles;

    // ── Particles ───────────────────────────────────────────────────────

    G.spawnParticle = function (type, wx, wy) {
        particles.push({
            type,
            wx, wy,
            birth: G.gameFrame,
            life: type === "dust" ? 30 : 40,
        });
    };

    // ── Map builder ─────────────────────────────────────────────────────

    G.buildMapImage = function () {
        if (!G.mapCached) return;
        const { cols, rows, tileSize, tiles } = G.mapCached;
        const spr = G.sprites;
        const posHash = G.posHash;

        mapCanvas = document.createElement("canvas");
        mapCanvas.width = cols * tileSize;
        mapCanvas.height = rows * tileSize;
        const mctx = mapCanvas.getContext("2d");
        decorations = [];
        waterRocks = [];

        const SRC_X = 1 * 64;
        const SRC_Y = 1 * 64;

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const tt = tiles[r][c];
                const px = c * tileSize;
                const py = r * tileSize;

                let tileset = null;
                if (tt === 0) tileset = spr.ts_grass;
                else if (tt === 1) tileset = spr.ts_dirt;
                else if (tt === 2) tileset = spr.ts_sand;
                else if (tt === 3) {
                    if (spr.water_bg) {
                        mctx.drawImage(spr.water_bg, px, py, tileSize, tileSize);
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
                    mctx.drawImage(tileset, SRC_X, SRC_Y, 64, 64, px, py, tileSize, tileSize);
                    if ((r + c) % 2 === 0) {
                        mctx.fillStyle = "rgba(0,0,0,0.04)";
                        mctx.fillRect(px, py, tileSize, tileSize);
                    }
                } else {
                    const colors = TILE_COLORS[tt] || TILE_COLORS[0];
                    const color = (r + c) % 2 === 0 ? colors.light : colors.dark;
                    mctx.fillStyle = color;
                    mctx.fillRect(px, py, tileSize, tileSize);
                }

                if (tt === 0 && posHash(c + 1, r + 3, 30) === 0) {
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
        clouds = [];
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
    };

    // ── Render loop ─────────────────────────────────────────────────────

    G.render = function () {
        if (!G.gameState || !G.mapCached) {
            requestAnimationFrame(G.render);
            return;
        }

        const canvas = G.canvas;
        const ctx = G.ctx;
        const W = canvas.width;
        const H = canvas.height;
        ctx.clearRect(0, 0, W, H);
        G.gameFrame++;

        G.updateCamera(W, H);

        // Map
        if (mapCanvas) ctx.drawImage(mapCanvas, -G.camX, -G.camY);

        const spr = G.sprites;

        // Water rocks
        for (const wr of waterRocks) {
            const dx = wr.x - G.camX;
            const dy = wr.y - G.camY;
            if (dx < -80 || dx > W + 80 || dy < -80 || dy > H + 80) continue;
            const wrSpr = spr["water_rock" + wr.variant];
            if (wrSpr) {
                const sz = 48;
                ctx.drawImage(wrSpr, dx - sz / 2, dy - sz / 2, sz, sz);
            }
        }

        // Bush decorations
        for (const deco of decorations) {
            const dx = deco.x - G.camX;
            const dy = deco.y - G.camY;
            if (dx < -64 || dx > W + 64 || dy < -64 || dy > H + 64) continue;
            const bushSpr = spr["bush" + deco.variant];
            if (bushSpr) {
                const sz = 30;
                const bushFrames = G.cfgFrames("bushes", 8);
                const fi = G.spriteFrame(bushFrames, G.cfgSpeed("bushes", "slow"), deco.offset);
                G.drawSpriteFrame(ctx, bushSpr, fi, bushFrames,
                    dx - sz / 2, dy - sz / 2, sz, sz, false);
            }
        }

        // 2.5D depth sort: merge resources + NPCs + fauna
        const ts = G.mapCached.tileSize;
        const drawList = [];
        for (const res of G.gameState.resources) {
            drawList.push({ type: "res", obj: res, footY: (res.row + 1) * ts });
        }
        for (const npc of G.gameState.npcs) {
            drawList.push({ type: "npc", obj: npc, footY: npc.y });
        }
        if (G.gameState.fauna) {
            for (const f of G.gameState.fauna) {
                drawList.push({ type: "fauna", obj: f, footY: f.y });
            }
        }
        drawList.sort((a, b) => a.footY - b.footY);

        for (const item of drawList) {
            if (item.type === "res") {
                const res = item.obj;
                const sx = res.col * ts + ts / 2 - G.camX;
                const sy = res.row * ts + ts / 2 - G.camY;
                if (sx < -ts * 3 || sx > W + ts * 3 || sy < -ts * 3 || sy > H + ts * 3) continue;
                drawResource(ctx, res, sx, sy, ts);
            } else if (item.type === "npc") {
                const npc = item.obj;
                const sx = npc.x - G.camX;
                const sy = npc.y - G.camY;
                if (sx < -80 || sx > W + 80 || sy < -80 || sy > H + 80) continue;
                drawNPC(ctx, npc, sx, sy);
            } else if (item.type === "fauna") {
                const f = item.obj;
                const sx = f.x - G.camX;
                const sy = f.y - G.camY;
                if (sx < -80 || sx > W + 80 || sy < -80 || sy > H + 80) continue;
                drawFauna(ctx, f, sx, sy);
            }
        }

        // Particle FX
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            const age = G.gameFrame - p.birth;
            if (age >= p.life) { particles.splice(i, 1); continue; }
            const progress = age / p.life;
            const px = p.wx - G.camX;
            const py = p.wy - G.camY;
            if (px < -64 || px > W + 64 || py < -64 || py > H + 64) continue;
            ctx.globalAlpha = 1 - progress;
            if (p.type === "dust") {
                const ds = spr.dust1 || spr.dust2;
                if (ds) {
                    const dustFrames = G.cfgFrames("dust_1", 8);
                    const fi = G.spriteFrame(dustFrames, G.cfgSpeed("dust_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, ds, fi, dustFrames, px - 24, py - 24, 48, 48, false);
                }
            } else if (p.type === "fire") {
                const fs = spr.fire1 || spr.fire2;
                if (fs) {
                    const fireFrames = G.cfgFrames("fire_1", 8);
                    const fi = G.spriteFrame(fireFrames, G.cfgSpeed("fire_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, fs, fi, fireFrames, px - 16, py - 32, 32, 32, false);
                }
            }
            ctx.globalAlpha = 1;
        }

        // Floating clouds
        if (G.mapCached) {
            const mapW = G.mapCached.cols * G.mapCached.tileSize;
            ctx.globalAlpha = 0.35;
            for (const cl of clouds) {
                cl.x = (cl.x + cl.speed) % (mapW + 300);
                const cx = cl.x - G.camX - 150;
                const cy = cl.y - G.camY;
                if (cx < -300 || cx > W + 300 || cy < -200 || cy > H + 200) continue;
                const cloudSpr = spr["cloud" + cl.variant];
                if (cloudSpr) {
                    const cw = 160 * cl.scale;
                    const ch = (cloudSpr.height / cloudSpr.width) * cw;
                    ctx.drawImage(cloudSpr, cx, cy, cw, ch);
                }
            }
            ctx.globalAlpha = 1;
        }

        // UI overlay
        G.updateUI();
        G.updateSpeechBubbles();

        requestAnimationFrame(G.render);
    };

    // ── Draw resource ───────────────────────────────────────────────────

    function drawResource(ctx, res, sx, sy, ts) {
        const spr = G.sprites;
        const posHash = G.posHash;

        switch (res.kind) {
            case "tree": {
                const v = posHash(res.col, res.row, 4) + 1;
                const sp = spr["tree" + v];
                if (sp) {
                    const treeFrames = G.cfgFrames("trees", 8);
                    const offset = posHash(res.col, res.row, treeFrames);
                    const frame = G.spriteFrame(treeFrames, G.cfgSpeed("trees", "slow"), offset);
                    const dw = ts * 2.0;
                    const dh = ts * 2.6;
                    G.drawSpriteFrame(ctx, sp, frame, treeFrames,
                        sx - dw / 2, sy - dh + ts * 0.5, dw, dh, false);
                } else {
                    ctx.fillStyle = "#795b3d";
                    ctx.fillRect(sx - 4, sy - 2, 8, 16);
                    ctx.fillStyle = "#388e3c";
                    ctx.beginPath(); ctx.arc(sx, sy - 10, 18, 0, Math.PI * 2); ctx.fill();
                    ctx.fillStyle = "#4caf50";
                    ctx.beginPath(); ctx.arc(sx - 3, sy - 14, 13, 0, Math.PI * 2); ctx.fill();
                }
                break;
            }
            case "rock": {
                if (res.hasGold) {
                    const v = posHash(res.col, res.row, 6) + 1;
                    const sp = spr["gold" + v];
                    if (sp) {
                        const sz = ts * 1.0;
                        ctx.drawImage(sp, sx - sz / 2, sy - sz / 2, sz, sz);
                        const hlSpr = spr["gold_hl" + v];
                        if (hlSpr) {
                            const hlFrames = G.cfgFrames("gold_highlight", 6);
                            const hlFrame = G.spriteFrame(hlFrames, G.cfgSpeed("gold_highlight", "slow"), posHash(res.col, res.row, 6));
                            ctx.globalAlpha = 0.6;
                            G.drawSpriteFrame(ctx, hlSpr, hlFrame, hlFrames, sx - sz / 2, sy - sz / 2, sz, sz, false);
                            ctx.globalAlpha = 1;
                        }
                    } else {
                        ctx.fillStyle = "#9e9e9e";
                        ctx.beginPath(); ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2); ctx.fill();
                        ctx.fillStyle = "#ffd700";
                        [[-5, -2], [3, 1], [-1, 4]].forEach(([dx, dy]) => {
                            ctx.beginPath(); ctx.arc(sx + dx, sy + dy, 2.5, 0, Math.PI * 2); ctx.fill();
                        });
                    }
                } else {
                    const v = posHash(res.col, res.row, 4) + 1;
                    const sp = spr["rock" + v];
                    if (sp) {
                        const sz = ts * 0.8;
                        ctx.drawImage(sp, sx - sz / 2, sy - sz / 2, sz, sz);
                    } else {
                        ctx.fillStyle = "#757575";
                        ctx.beginPath(); ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2); ctx.fill();
                    }
                }
                break;
            }
            case "structure": {
                const isHut = res.buildingType === "storage_hut";
                const houseKey = isHut ? "house1" : "house" + (posHash(res.col, res.row, 3) + 1);
                const houseSpr = spr[houseKey] || spr.house1;
                if (res.built) {
                    if (houseSpr) {
                        const dw = ts * 2, dh = ts * 3;
                        ctx.drawImage(houseSpr, sx - dw / 2, sy - dh + ts * 0.6, dw, dh);
                    } else {
                        ctx.fillStyle = "#654321"; ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#503018"; ctx.lineWidth = 2; ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                        ctx.fillStyle = "#b22222"; ctx.beginPath();
                        ctx.moveTo(sx - 24, sy - 20); ctx.lineTo(sx + 24, sy - 20); ctx.lineTo(sx, sy - 38);
                        ctx.closePath(); ctx.fill();
                    }
                    // Storage Hut label
                    if (isHut) {
                        ctx.font = "bold 10px 'JetBrains Mono', Consolas, monospace";
                        ctx.textAlign = "center";
                        ctx.fillStyle = "rgba(0,0,0,0.6)";
                        ctx.fillText("\u26fa Storage Hut", sx + 1, sy - ts * 2.1 + 1);
                        ctx.fillStyle = "#ffe066";
                        ctx.fillText("\u26fa Storage Hut", sx, sy - ts * 2.1);
                    }
                } else {
                    if (houseSpr) {
                        ctx.globalAlpha = 0.2 + 0.8 * (res.buildProgress / 100);
                        const dw = ts * 2, dh = ts * 3;
                        ctx.drawImage(houseSpr, sx - dw / 2, sy - dh + ts * 0.6, dw, dh);
                        ctx.globalAlpha = 1;
                    } else {
                        ctx.fillStyle = "#8b7765"; ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#50403c"; ctx.lineWidth = 2; ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                    }
                    drawBar(ctx, sx, sy - ts - 10, 36, 5, res.buildProgress / 100, "#4caf50");
                }
                break;
            }
            case "wheat": {
                const half = ts / 2 - 2;
                const gr = res.growthRatio;         // 0 → 1
                const sway = Math.sin(G.gameFrame / 28 + posHash(res.col, res.row, 100)) * 1.5 * gr;

                const px = sx - half, py = sy - half + 6;
                const pw = half * 2, ph = half * 2 - 6;

                // ── Wheat stalks ──
                const stalkCount = 5;
                const spacing = (pw - 8) / (stalkCount - 1);
                const maxStalkH = ts * 0.65;
                const stalkH = 4 + maxStalkH * gr;

                for (let i = 0; i < stalkCount; i++) {
                    const bx = px + 4 + i * spacing;
                    const baseY = py + ph - 2;
                    const tipX = bx + sway + (i % 2 === 0 ? sway * 0.3 : -sway * 0.3);
                    const tipY = baseY - stalkH;

                    // Stalk color transitions green → golden
                    const stalkR = Math.floor(75 + 145 * gr);
                    const stalkG = Math.floor(130 + 90 * gr);
                    const stalkB = Math.floor(30 - 10 * gr);

                    // Thick outlined stalk (pixel-art style)
                    ctx.strokeStyle = `rgb(${Math.floor(stalkR * 0.55)},${Math.floor(stalkG * 0.55)},${Math.floor(stalkB * 0.6)})`;
                    ctx.lineWidth = 4; ctx.lineCap = "round";
                    ctx.beginPath(); ctx.moveTo(bx, baseY); ctx.lineTo(tipX, tipY); ctx.stroke();
                    ctx.strokeStyle = `rgb(${stalkR},${stalkG},${stalkB})`;
                    ctx.lineWidth = 2;
                    ctx.beginPath(); ctx.moveTo(bx, baseY); ctx.lineTo(tipX, tipY); ctx.stroke();

                    // Leaf sprout (small triangle on stalk, only when partially grown)
                    if (gr > 0.2 && gr < 0.85) {
                        const leafY = baseY - stalkH * 0.4;
                        const leafDir = i % 2 === 0 ? 1 : -1;
                        ctx.fillStyle = `rgb(${stalkR},${Math.min(255, stalkG + 20)},${stalkB})`;
                        ctx.beginPath();
                        ctx.moveTo(bx + sway * 0.4, leafY);
                        ctx.lineTo(bx + sway * 0.4 + leafDir * 5, leafY - 2);
                        ctx.lineTo(bx + sway * 0.4 + leafDir * 2, leafY + 3);
                        ctx.closePath(); ctx.fill();
                    }

                    // Wheat head (only when > 50% grown)
                    if (gr > 0.5) {
                        const headAlpha = Math.min(1, (gr - 0.5) * 4);
                        const headW = 3 + 2 * gr;
                        const headH = 4 + 5 * gr;
                        ctx.globalAlpha = headAlpha;
                        // Outline
                        ctx.fillStyle = "#8b6914";
                        roundRect(ctx, tipX - headW - 0.5, tipY - headH - 0.5, headW * 2 + 1, headH + 1, 2);
                        ctx.fill();
                        // Body
                        ctx.fillStyle = gr > 0.85 ? "#f0c535" : "#c8a82e";
                        roundRect(ctx, tipX - headW, tipY - headH, headW * 2, headH, 2);
                        ctx.fill();
                        // Inner highlight
                        ctx.fillStyle = "rgba(255,245,180,0.4)";
                        roundRect(ctx, tipX - headW + 1, tipY - headH + 1, headW * 2 - 2, headH * 0.4, 1);
                        ctx.fill();
                        // Tiny awns (spiky top)
                        ctx.strokeStyle = gr > 0.85 ? "#d4a820" : "#9e8524";
                        ctx.lineWidth = 1; ctx.lineCap = "round";
                        for (let a = -1; a <= 1; a++) {
                            ctx.beginPath();
                            ctx.moveTo(tipX + a * 2, tipY - headH);
                            ctx.lineTo(tipX + a * 3 + sway * 0.5, tipY - headH - 3 - gr * 2);
                            ctx.stroke();
                        }
                        ctx.globalAlpha = 1;
                    }
                }

                // ── Growth indicator ──
                if (!res.fullyGrown) {
                    drawBar(ctx, sx, py - 6, 30, 5, gr, "#7cb342");
                } else {
                    // Golden sparkle particles for READY state
                    const sparkleT = G.gameFrame / 15;
                    ctx.globalAlpha = 0.7 + 0.3 * Math.sin(sparkleT);
                    ctx.fillStyle = "#ffe066";
                    for (let si = 0; si < 3; si++) {
                        const sa = sparkleT + si * 2.1 + posHash(res.col, res.row, 10);
                        const sparkX = sx + Math.cos(sa) * (half * 0.7);
                        const sparkY = py + ph * 0.3 + Math.sin(sa * 1.3) * (half * 0.4);
                        const ss = 1.5 + Math.sin(sparkleT + si) * 0.8;
                        ctx.beginPath();
                        // 4-pointed star
                        ctx.moveTo(sparkX, sparkY - ss * 2);
                        ctx.lineTo(sparkX + ss * 0.6, sparkY - ss * 0.6);
                        ctx.lineTo(sparkX + ss * 2, sparkY);
                        ctx.lineTo(sparkX + ss * 0.6, sparkY + ss * 0.6);
                        ctx.lineTo(sparkX, sparkY + ss * 2);
                        ctx.lineTo(sparkX - ss * 0.6, sparkY + ss * 0.6);
                        ctx.lineTo(sparkX - ss * 2, sparkY);
                        ctx.lineTo(sparkX - ss * 0.6, sparkY - ss * 0.6);
                        ctx.closePath(); ctx.fill();
                    }
                    ctx.globalAlpha = 1;
                }
                break;
            }
        }
        if (res.hp < res.maxHp && res.kind !== "wheat" && res.kind !== "structure") {
            drawBar(ctx, sx, sy - ts / 2 - 8, 30, 5, res.hp / res.maxHp, "#4caf50");
        }
    }

    // ── Draw NPC ────────────────────────────────────────────────────────

    function getNpcSprite(npc) {
        const spr = G.sprites;
        const st = npc.state;
        const act = npc.actionType || "";
        const carrying = npc.carrying || {};
        const hasWood  = (carrying.wood  || 0) > 0;
        const hasGold  = (carrying.gold  || 0) > 0;

        // ── Carrying sprites (RETURNING to hut or idle while carrying) ──
        if (npc.isCarrying) {
            if (st === "RETURNING" || st === "MOVING") {
                if (hasWood)  return { spr: spr.pawn_run_wood  || spr.pawn_run, frames: G.cfgFrames("pawn_run_wood",  6), speed: G.cfgSpeed("pawn_run_wood",  "fast") };
                if (hasGold)  return { spr: spr.pawn_run_gold  || spr.pawn_run, frames: G.cfgFrames("pawn_run_gold",  6), speed: G.cfgSpeed("pawn_run_gold",  "fast") };
                // stone / wheat – reuse wood carry sprite
                return { spr: spr.pawn_run_wood  || spr.pawn_run, frames: G.cfgFrames("pawn_run_wood", 6), speed: G.cfgSpeed("pawn_run_wood", "fast") };
            }
            // idle while carrying
            if (hasWood)  return { spr: spr.pawn_idle_wood || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_wood", 8), speed: G.cfgSpeed("pawn_idle_wood", "normal") };
            if (hasGold)  return { spr: spr.pawn_idle_gold || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_gold", 8), speed: G.cfgSpeed("pawn_idle_gold", "normal") };
            return { spr: spr.pawn_idle_wood || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_wood", 8), speed: G.cfgSpeed("pawn_idle_wood", "normal") };
        }

        if (st === "MOVING") {
            switch (act) {
                case "chop_wood":  return { spr: spr.pawn_run_axe  || spr.pawn_run, frames: G.cfgFrames("pawn_run_axe", 6), speed: G.cfgSpeed("pawn_run_axe", "fast") };
                case "mine_rock":  return { spr: spr.pawn_run_pick || spr.pawn_run, frames: G.cfgFrames("pawn_run_pickaxe", 6), speed: G.cfgSpeed("pawn_run_pickaxe", "fast") };
                case "build":      return { spr: spr.pawn_run_ham  || spr.pawn_run, frames: G.cfgFrames("pawn_run_hammer", 6), speed: G.cfgSpeed("pawn_run_hammer", "fast") };
                default:           return { spr: spr.pawn_run, frames: G.cfgFrames("pawn_run", 6), speed: G.cfgSpeed("pawn_run", "fast") };
            }
        }

        if (st === "PERFORMING") {
            switch (act) {
                case "chop_wood":
                    if (G.gameFrame % 20 === 0) G.spawnParticle("dust", npc.x, npc.y + 5);
                    return { spr: spr.pawn_act_axe,   frames: G.cfgFrames("pawn_interact_axe", 6),     speed: G.cfgSpeed("pawn_interact_axe", "fast") };
                case "mine_rock":
                    if (G.gameFrame % 18 === 0) G.spawnParticle("fire", npc.x, npc.y - 10);
                    return { spr: spr.pawn_act_pick,  frames: G.cfgFrames("pawn_interact_pickaxe", 6), speed: G.cfgSpeed("pawn_interact_pickaxe", "fast") };
                case "build":
                    if (G.gameFrame % 25 === 0) G.spawnParticle("dust", npc.x, npc.y + 5);
                    return { spr: spr.pawn_act_ham,   frames: G.cfgFrames("pawn_interact_hammer", 3),  speed: G.cfgSpeed("pawn_interact_hammer", "fast") };
                case "plant_wheat":
                case "collect_wheat":
                    return { spr: spr.pawn_act_knife, frames: G.cfgFrames("pawn_interact_knife", 6),   speed: G.cfgSpeed("pawn_interact_knife", "fast") };
                case "eat":
                    return { spr: spr.pawn_idle_meat, frames: G.cfgFrames("pawn_idle_meat", 8),        speed: G.cfgSpeed("pawn_idle_meat", "normal") };
                default:
                    return { spr: spr.pawn_idle,      frames: G.cfgFrames("pawn_idle", 8),             speed: G.cfgSpeed("pawn_idle", "normal") };
            }
        }

        switch (act) {
            case "chop_wood":  return { spr: spr.pawn_idle_axe  || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_axe", 8),     speed: G.cfgSpeed("pawn_idle_axe", "normal") };
            case "mine_rock":  return { spr: spr.pawn_idle_pick || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_pickaxe", 8), speed: G.cfgSpeed("pawn_idle_pickaxe", "normal") };
            case "build":      return { spr: spr.pawn_idle_ham  || spr.pawn_idle, frames: G.cfgFrames("pawn_idle_hammer", 8),  speed: G.cfgSpeed("pawn_idle_hammer", "normal") };
            default:           return { spr: spr.pawn_idle,                       frames: G.cfgFrames("pawn_idle", 8),         speed: G.cfgSpeed("pawn_idle", "normal") };
        }
    }

    function drawNPC(ctx, npc, sx, sy) {
        const spr = G.sprites;
        const SIZE = 64;
        const HALF = SIZE / 2;
        const facingRight = G.updateFacing(npc);

        // Shadow
        if (spr.shadow) {
            ctx.globalAlpha = 0.25;
            ctx.drawImage(spr.shadow, 0, 0, 192, 192, sx - HALF * 0.7, sy - 4, SIZE * 0.7, SIZE * 0.35);
            ctx.globalAlpha = 1;
        } else {
            ctx.fillStyle = "rgba(0,0,0,0.25)";
            ctx.beginPath(); ctx.ellipse(sx, sy, HALF * 0.6, HALF * 0.25, 0, 0, Math.PI * 2); ctx.fill();
        }

        // Selection ring
        if (npc.selected) {
            ctx.strokeStyle = "#00e676"; ctx.lineWidth = 2.5;
            ctx.beginPath(); ctx.ellipse(sx, sy + 2, HALF + 4, HALF * 0.35 + 2, 0, 0, Math.PI * 2); ctx.stroke();
        }

        // Sprite
        const info = getNpcSprite(npc);
        const frame = G.spriteFrame(info.frames, info.speed, npc.id);
        const spriteDrawn = info.spr && G.drawSpriteFrame(ctx, info.spr, frame, info.frames,
            sx - HALF, sy - SIZE + 10, SIZE, SIZE, !facingRight);

        if (!spriteDrawn) {
            const bob = npc.state === "IDLE" ? Math.sin(Date.now() / 200) * 2 : 0;
            const by = sy + bob;
            ctx.fillStyle = "#ffb74d";
            ctx.beginPath(); ctx.arc(sx, by - 14, 14, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = npc.selected ? "#00e676" : "#e6801e"; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(sx, by - 14, 14, 0, Math.PI * 2); ctx.stroke();
            ctx.fillStyle = "#333";
            ctx.beginPath(); ctx.arc(sx - 4, by - 17, 2, 0, Math.PI * 2); ctx.arc(sx + 4, by - 17, 2, 0, Math.PI * 2); ctx.fill();
        }

        // Name
        ctx.font = "bold 11px Consolas"; ctx.textAlign = "center";
        ctx.fillStyle = "rgba(0,0,0,0.7)"; ctx.fillText(npc.name, sx + 1, sy - SIZE + 4);
        ctx.fillStyle = "#fff"; ctx.fillText(npc.name, sx, sy - SIZE + 3);

        // State
        ctx.font = "9px Consolas"; ctx.fillStyle = "#ddd";
        ctx.fillText(npc.state, sx, sy - SIZE + 14);

        // HP bar
        if (npc.health < npc.maxHealth) {
            drawBar(ctx, sx, sy - SIZE - 2, 28, 4, npc.health / npc.maxHealth, "#4caf50");
        }

        // Hunger bar
        const hungerRatio = npc.hunger / npc.maxHunger;
        drawBar(ctx, sx, sy + 8, 24, 4, hungerRatio, hungerRatio > 0.25 ? "#ff9800" : "#f44336");

        // Carrying indicator (small emoji badge next to name)
        if (npc.isCarrying) {
            const carry = npc.carrying || {};
            let icon = "\ud83e\udea8";  // generic
            if (carry.wood  > 0) icon = "\ud83e\udeb5";
            if (carry.gold  > 0) icon = "\ud83e\ude99";
            if (carry.stone > 0) icon = "\ud83e\udea8";
            if (carry.wheat > 0) icon = "\ud83c\udf3e";
            ctx.font = "12px serif";
            ctx.fillText(icon, sx + 18, sy - SIZE + 6);
        }
    }

    // ── Draw Fauna (autonomous creatures like sheep) ──────────────────

    const LECHAT_FRAMES = 27;
    const LECHAT_ANIM_INTERVAL = 6;  // game frames per animation frame

    function getFaunaSpriteInfo(f) {
        const spr = G.sprites;
        const st = f.state;

        if (f.kind === "cat") return null;  // cat uses individual frames

        if (st === "GRAZING") {
            return {
                spr: spr.sheep_grass,
                frames: G.cfgFrames("sheep_grass", 12),
                speed: G.cfgSpeed("sheep_grass", "normal"),
            };
        }
        if (st === "WANDERING") {
            return {
                spr: spr.sheep_move,
                frames: G.cfgFrames("sheep_move", 4),
                speed: G.cfgSpeed("sheep_move", "normal"),
            };
        }
        // IDLE
        return {
            spr: spr.sheep_idle,
            frames: G.cfgFrames("sheep_idle", 6),
            speed: G.cfgSpeed("sheep_idle", "normal"),
        };
    }

    function drawFauna(ctx, f, sx, sy) {
        if (f.kind === "cat") {
            drawCat(ctx, f, sx, sy);
            return;
        }

        const spr = G.sprites;
        const SIZE = 48;
        const HALF = SIZE / 2;
        const facingRight = G.updateFacing(f);

        // Shadow
        if (spr.shadow) {
            ctx.globalAlpha = 0.2;
            ctx.drawImage(spr.shadow, 0, 0, 192, 192, sx - HALF * 0.6, sy - 2, SIZE * 0.6, SIZE * 0.25);
            ctx.globalAlpha = 1;
        } else {
            ctx.fillStyle = "rgba(0,0,0,0.18)";
            ctx.beginPath(); ctx.ellipse(sx, sy, HALF * 0.5, HALF * 0.2, 0, 0, Math.PI * 2); ctx.fill();
        }

        // Sprite
        const info = getFaunaSpriteInfo(f);
        const frame = G.spriteFrame(info.frames, info.speed, f.id);
        const spriteDrawn = info.spr && G.drawSpriteFrame(ctx, info.spr, frame, info.frames,
            sx - HALF, sy - SIZE + 12, SIZE, SIZE, !facingRight);

        if (!spriteDrawn) {
            // Fallback: simple colored ellipse
            ctx.fillStyle = "#e8e0d0";
            ctx.beginPath(); ctx.ellipse(sx, sy - 10, 14, 10, 0, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = "#d0c8b8";
            ctx.beginPath(); ctx.arc(sx + 10, sy - 12, 6, 0, Math.PI * 2); ctx.fill();
        }

        // HP bar (only if damaged)
        if (f.health < f.maxHealth) {
            drawBar(ctx, sx, sy - SIZE + 2, 24, 3, f.health / f.maxHealth, "#4caf50");
        }
    }

    // ── Draw Cat (individual-frame animation) ───────────────────────────

    function drawCat(ctx, f, sx, sy) {
        const spr = G.sprites;
        const SIZE = 80;
        const HALF = SIZE / 2;

        // Shadow
        if (spr.shadow) {
            ctx.globalAlpha = 0.2;
            ctx.drawImage(spr.shadow, 0, 0, 192, 192, sx - HALF * 0.5, sy - 2, SIZE * 0.5, SIZE * 0.2);
            ctx.globalAlpha = 1;
        }

        // Pick the right frame from the 27 individual images
        const fi = Math.floor(G.gameFrame / LECHAT_ANIM_INTERVAL) % LECHAT_FRAMES;
        const frameImg = spr["lechat_" + fi];
        if (frameImg) {
            ctx.drawImage(frameImg, sx - HALF, sy - SIZE + 16, SIZE, SIZE);
        } else {
            // Fallback
            ctx.fillStyle = "#555";
            ctx.beginPath(); ctx.ellipse(sx, sy - 8, 12, 8, 0, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = "#444";
            ctx.beginPath(); ctx.arc(sx + 8, sy - 14, 5, 0, Math.PI * 2); ctx.fill();
        }

        // Name label
        ctx.font = "bold 10px Consolas"; ctx.textAlign = "center";
        ctx.fillStyle = "rgba(0,0,0,0.6)"; ctx.fillText(f.name, sx + 1, sy - SIZE + 10);
        ctx.fillStyle = "#fff"; ctx.fillText(f.name, sx, sy - SIZE + 9);
    }

    // ── Drawing helpers ─────────────────────────────────────────────────

    function drawBar(ctx, cx, top, w, h, ratio, color) {
        const x = cx - w / 2;
        ctx.fillStyle = "#3c3c3c"; ctx.fillRect(x, top, w, h);
        if (ratio > 0) {
            ctx.fillStyle = color;
            ctx.fillRect(x, top, w * Math.max(0, Math.min(1, ratio)), h);
        }
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

})(window.G4AL);
