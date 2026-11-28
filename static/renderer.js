/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Rendering Loop, Resource & NPC Drawing
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // Pixels past the canvas edges where a unit, a creature or a water rock is still drawn.
    const OFFSCREEN_MARGIN = 80;
    // Pixels past the canvas edges where a bush, a particle or an arrow is still drawn.
    const SMALL_OFFSCREEN_MARGIN = 64;
    // Side, in pixels, of the source image of Shadow.png.
    const SHADOW_SPRITE_SIZE = 192;
    // Fewest game frames between two arrow sounds.
    const ARROW_SFX_COOLDOWN_FRAMES = 20;
    // Game frames per animation frame of the cat.
    const CAT_ANIMATION_INTERVAL = 6;

    const particles = [];
    G.particles = particles;

    // ── Arrow SFX (procedural Web Audio) ────────────────────────────────

    let _arrowSfxCooldown = 0;
    let _audioCtx = null;

    function playArrowSfx() {
        if (G.gameFrame - _arrowSfxCooldown < ARROW_SFX_COOLDOWN_FRAMES) return;
        _arrowSfxCooldown = G.gameFrame;
        try {
            if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const ctx = _audioCtx;
            const t = ctx.currentTime;
            // Quick "twang" noise burst
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sawtooth";
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.setValueAtTime(600, t);
            osc.frequency.exponentialRampToValueAtTime(120, t + 0.12);
            gain.gain.setValueAtTime(0.15, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
            osc.start(t);
            osc.stop(t + 0.18);
        } catch (e) { /* audio not available */ }
    }

    // ── Particles ───────────────────────────────────────────────────────

    G.spawnParticle = function (type, wx, wy) {
        particles.push({
            type,
            wx, wy,
            birth: G.gameFrame,
            life: type === "dust" ? 30 : 40,
        });
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
        const { canvas: mapCanvas, waterRocks, decorations, clouds } = G.mapLayers;
        if (mapCanvas) ctx.drawImage(mapCanvas, -G.camX, -G.camY);

        const sprites = G.sprites;

        // Water rocks
        for (const wr of waterRocks) {
            const dx = wr.x - G.camX;
            const dy = wr.y - G.camY;
            if (dx < -OFFSCREEN_MARGIN || dx > W + OFFSCREEN_MARGIN || dy < -OFFSCREEN_MARGIN || dy > H + OFFSCREEN_MARGIN) continue;
            const wrSpr = sprites["water_rock" + wr.variant];
            if (wrSpr) {
                const spriteSize = 48;
                ctx.drawImage(wrSpr, dx - spriteSize / 2, dy - spriteSize / 2, spriteSize, spriteSize);
            }
        }

        // Bush decorations
        for (const deco of decorations) {
            const dx = deco.x - G.camX;
            const dy = deco.y - G.camY;
            if (dx < -SMALL_OFFSCREEN_MARGIN || dx > W + SMALL_OFFSCREEN_MARGIN || dy < -SMALL_OFFSCREEN_MARGIN || dy > H + SMALL_OFFSCREEN_MARGIN) continue;
            const bushSpr = sprites["bush" + deco.variant];
            if (bushSpr) {
                const spriteSize = 30;
                const bushFrames = G.readFrameCount("bushes", 8);
                const fi = G.spriteFrame(bushFrames, G.readAnimationSpeed("bushes", "slow"), deco.offset);
                G.drawSpriteFrame(ctx, bushSpr, fi, bushFrames,
                    dx - spriteSize / 2, dy - spriteSize / 2, spriteSize, spriteSize, false);
            }
        }

        // 2.5D depth sort: merge resources + NPCs + fauna
        const ts = G.mapCached.tileSize;
        const drawList = [];
        for (const resource of G.gameState.resources) {
            drawList.push({ type: "resource", obj: resource, footY: (resource.row + resource.footprint.depth) * ts });
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
            if (item.type === "resource") {
                const resource = item.obj;
                const sx = resource.col * ts + (resource.footprint.width * ts) / 2 - G.camX;
                const sy = resource.row * ts + (resource.footprint.depth * ts) / 2 - G.camY;
                if (sx < -ts * 3 || sx > W + ts * 3 || sy < -ts * 3 || sy > H + ts * 3) continue;
                drawResource(ctx, resource, sx, sy, ts);
            } else if (item.type === "npc") {
                const npc = item.obj;
                const sx = npc.x - G.camX;
                const sy = npc.y - G.camY;
                if (sx < -OFFSCREEN_MARGIN || sx > W + OFFSCREEN_MARGIN || sy < -OFFSCREEN_MARGIN || sy > H + OFFSCREEN_MARGIN) continue;
                drawNPC(ctx, npc, sx, sy);
            } else if (item.type === "fauna") {
                const f = item.obj;
                const sx = f.x - G.camX;
                const sy = f.y - G.camY;
                if (sx < -OFFSCREEN_MARGIN || sx > W + OFFSCREEN_MARGIN || sy < -OFFSCREEN_MARGIN || sy > H + OFFSCREEN_MARGIN) continue;
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
            if (px < -SMALL_OFFSCREEN_MARGIN || px > W + SMALL_OFFSCREEN_MARGIN || py < -SMALL_OFFSCREEN_MARGIN || py > H + SMALL_OFFSCREEN_MARGIN) continue;
            ctx.globalAlpha = 1 - progress;
            if (p.type === "dust") {
                const ds = sprites.dust1 || sprites.dust2;
                if (ds) {
                    const dustFrames = G.readFrameCount("dust_1", 8);
                    const fi = G.spriteFrame(dustFrames, G.readAnimationSpeed("dust_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, ds, fi, dustFrames, px - 24, py - 24, 48, 48, false);
                }
            } else if (p.type === "fire") {
                const fs = sprites.fire1 || sprites.fire2;
                if (fs) {
                    const fireFrames = G.readFrameCount("fire_1", 8);
                    const fi = G.spriteFrame(fireFrames, G.readAnimationSpeed("fire_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, fs, fi, fireFrames, px - 16, py - 32, 32, 32, false);
                }
            }
            ctx.globalAlpha = 1;
        }

        if (G.gameState.arrows) {
            for (const arrow of G.gameState.arrows) {
                const p = arrow.progress;
                // The state carries no "arrow fired" event: a fresh arrow is one early in its flight.
                if (p < 0.15) playArrowSfx();
                const ax = arrow.fromX + (arrow.toX - arrow.fromX) * p;
                const ay = arrow.fromY + (arrow.toY - arrow.fromY) * p;
                const sx = ax - G.camX;
                const sy = ay - G.camY;
                if (sx < -SMALL_OFFSCREEN_MARGIN || sx > W + SMALL_OFFSCREEN_MARGIN || sy < -SMALL_OFFSCREEN_MARGIN || sy > H + SMALL_OFFSCREEN_MARGIN) continue;

                const dx = arrow.toX - arrow.fromX;
                const dy = arrow.toY - arrow.fromY;
                const angle = Math.atan2(dy, dx);

                const arrowSpr = arrow.team === "red" ? sprites.red_archer_arrow : sprites.archer_arrow;
                if (arrowSpr) {
                    ctx.save();
                    ctx.translate(sx, sy);
                    ctx.rotate(angle);
                    const aw = 28, ah = 10;
                    ctx.drawImage(arrowSpr, -aw / 2, -ah / 2, aw, ah);
                    ctx.restore();
                } else {
                    // Drawn by hand while the arrow sprite has not loaded.
                    const color = arrow.team === "red" ? "#ef5350" : "#42a5f5";
                    ctx.save();
                    ctx.translate(sx, sy);
                    ctx.rotate(angle);
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2.5;
                    ctx.beginPath();
                    ctx.moveTo(-12, 0);
                    ctx.lineTo(12, 0);
                    ctx.stroke();
                    // Arrowhead
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.moveTo(12, 0);
                    ctx.lineTo(7, -3);
                    ctx.lineTo(7, 3);
                    ctx.closePath();
                    ctx.fill();
                    ctx.restore();
                }

                // Fade out near the end
                if (p > 0.8) {
                    ctx.globalAlpha = 1 - (p - 0.8) / 0.2;
                }
                ctx.globalAlpha = 1;
            }
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
                const cloudSpr = sprites["cloud" + cl.variant];
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
        if (G._checkStorageFullAlert) G._checkStorageFullAlert();

        requestAnimationFrame(G.render);
    };

    // ── Draw resource ───────────────────────────────────────────────────

    /** Screen rectangle of an object's sprite; a resource's ground point is the bottom centre of its footprint. */
    function spriteRect(obj, groundX, groundY, ts) {
        const box = obj.sprite;
        return {
            left: groundX - box.anchorX * ts,
            top: groundY - box.anchorY * ts,
            width: box.width * ts, height: box.height * ts,
        };
    }

    function drawResource(ctx, resource, sx, sy, ts) {
        const sprites = G.sprites;
        const posHash = G.posHash;
        const rect = spriteRect(resource, sx, sy + (resource.footprint.depth * ts) / 2, ts);

        switch (resource.kind) {
            case "tree": {
                const v = posHash(resource.col, resource.row, 4) + 1;
                const sp = sprites["tree" + v];
                if (sp) {
                    const treeFrames = G.readFrameCount("trees", 8);
                    const offset = posHash(resource.col, resource.row, treeFrames);
                    const frame = G.spriteFrame(treeFrames, G.readAnimationSpeed("trees", "slow"), offset);
                    G.drawSpriteFrame(ctx, sp, frame, treeFrames,
                        rect.left, rect.top, rect.width, rect.height, false);
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
                if (resource.hasGold) {
                    const v = posHash(resource.col, resource.row, 6) + 1;
                    const sp = sprites["gold" + v];
                    if (sp) {
                        ctx.drawImage(sp, rect.left, rect.top, rect.width, rect.height);
                        const hlSpr = sprites["gold_hl" + v];
                        if (hlSpr) {
                            const hlFrames = G.readFrameCount("gold_highlight", 6);
                            const hlFrame = G.spriteFrame(hlFrames, G.readAnimationSpeed("gold_highlight", "slow"), posHash(resource.col, resource.row, 6));
                            ctx.globalAlpha = 0.6;
                            G.drawSpriteFrame(ctx, hlSpr, hlFrame, hlFrames, rect.left, rect.top, rect.width, rect.height, false);
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
                    const v = posHash(resource.col, resource.row, 4) + 1;
                    const sp = sprites["rock" + v];
                    if (sp) {
                        ctx.drawImage(sp, rect.left, rect.top, rect.width, rect.height);
                    } else {
                        ctx.fillStyle = "#757575";
                        ctx.beginPath(); ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2); ctx.fill();
                    }
                }
                break;
            }
            case "structure": {
                const isHut = resource.buildingType === "storage_hut";
                const houseKey = isHut ? "house1" : "house" + (posHash(resource.col, resource.row, 3) + 1);
                const houseSpr = sprites[houseKey] || sprites.house1;
                if (resource.built) {
                    if (houseSpr) {
                        ctx.drawImage(houseSpr, rect.left, rect.top, rect.width, rect.height);
                    } else {
                        ctx.fillStyle = "#654321"; ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#503018"; ctx.lineWidth = 2; ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                        ctx.fillStyle = "#b22222"; ctx.beginPath();
                        ctx.moveTo(sx - 24, sy - 20); ctx.lineTo(sx + 24, sy - 20); ctx.lineTo(sx, sy - 38);
                        ctx.closePath(); ctx.fill();
                    }
                    // Storage Hut label (pixel-art style) + capacity
                    if (isHut) {
                        const label = "STORAGE HUT";
                        const ly = rect.top - 8;
                        ctx.font = "bold 9px Consolas, monospace";
                        ctx.textAlign = "center";
                        ctx.letterSpacing = "2px";
                        // thick dark outline
                        ctx.fillStyle = "#2a1a08";
                        for (let ox = -1; ox <= 1; ox++)
                            for (let oy = -1; oy <= 1; oy++)
                                if (ox || oy) ctx.fillText(label, sx + ox, ly + oy);
                        // bright fill
                        ctx.fillStyle = "#f5deb3";
                        ctx.fillText(label, sx, ly);
                        ctx.letterSpacing = "0px";

                        // capacity bar under the label
                        if (G.gameState && G.gameState.storage) {
                            const used = G.gameState.storage.total || 0;
                            const cap  = G.gameState.storage.capacity || 50;
                            const ratio = cap > 0 ? Math.min(1, used / cap) : 0;
                            const barW = 44, barH = 4;
                            const bx = sx - barW / 2, by = ly + 4;
                            ctx.fillStyle = "#1a1008";
                            ctx.fillRect(bx - 1, by - 1, barW + 2, barH + 2);
                            ctx.fillStyle = "#333";
                            ctx.fillRect(bx, by, barW, barH);
                            ctx.fillStyle = ratio >= 1 ? "#e74c3c" : ratio >= 0.8 ? "#f39c12" : "#8bc34a";
                            ctx.fillRect(bx, by, barW * ratio, barH);
                            // capacity text
                            ctx.font = "bold 7px Consolas, monospace";
                            ctx.fillStyle = "#fff";
                            ctx.fillText(used + "/" + cap, sx, by + barH + 8);
                        }
                    }
                } else {
                    if (houseSpr) {
                        ctx.globalAlpha = 0.2 + 0.8 * (resource.buildProgress / 100);
                        ctx.drawImage(houseSpr, rect.left, rect.top, rect.width, rect.height);
                        ctx.globalAlpha = 1;
                    } else {
                        ctx.fillStyle = "#8b7765"; ctx.fillRect(sx - 20, sy - 20, 40, 40);
                        ctx.strokeStyle = "#50403c"; ctx.lineWidth = 2; ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                    }
                    drawBar(ctx, sx, rect.top - 10, 36, 5, resource.buildProgress / 100, "#4caf50");
                }
                break;
            }
            case "wheat": {
                const half = ts / 2 - 2;
                const gr = resource.growthRatio;         // 0 → 1
                const sway = Math.sin(G.gameFrame / 28 + posHash(resource.col, resource.row, 100)) * 1.5 * gr;

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
                if (!resource.fullyGrown) {
                    drawBar(ctx, sx, py - 6, 30, 5, gr, "#7cb342");
                } else {
                    // Golden sparkle particles for READY state
                    const sparkleT = G.gameFrame / 15;
                    ctx.globalAlpha = 0.7 + 0.3 * Math.sin(sparkleT);
                    ctx.fillStyle = "#ffe066";
                    for (let si = 0; si < 3; si++) {
                        const sa = sparkleT + si * 2.1 + posHash(resource.col, resource.row, 10);
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
        if (resource.hp < resource.maxHp && resource.kind !== "wheat" && resource.kind !== "structure") {
            drawBar(ctx, sx, sy - ts / 2 - 8, 30, 5, resource.hp / resource.maxHp, "#4caf50");
        }
    }

    // ── Draw NPC ────────────────────────────────────────────────────────

    function getNpcSprite(npc) {
        const sprites = G.sprites;
        const state = npc.state;
        const actionType = npc.actionType || "";
        const carrying = npc.carrying || {};
        const hasWood  = (carrying.wood  || 0) > 0;
        const hasGold  = (carrying.gold  || 0) > 0;

        // ── Carrying sprites (RETURNING to hut or idle while carrying) ──
        if (npc.isCarrying) {
            if (state === "RETURNING" || state === "MOVING") {
                if (hasWood)  return { sprite: sprites.pawn_run_wood  || sprites.pawn_run, frames: G.readFrameCount("pawn_run_wood",  6), speed: G.readAnimationSpeed("pawn_run_wood",  "fast") };
                if (hasGold)  return { sprite: sprites.pawn_run_gold  || sprites.pawn_run, frames: G.readFrameCount("pawn_run_gold",  6), speed: G.readAnimationSpeed("pawn_run_gold",  "fast") };
                // stone / wheat – reuse wood carry sprite
                return { sprite: sprites.pawn_run_wood  || sprites.pawn_run, frames: G.readFrameCount("pawn_run_wood", 6), speed: G.readAnimationSpeed("pawn_run_wood", "fast") };
            }
            // idle while carrying
            if (hasWood)  return { sprite: sprites.pawn_idle_wood || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_wood", 8), speed: G.readAnimationSpeed("pawn_idle_wood", "normal") };
            if (hasGold)  return { sprite: sprites.pawn_idle_gold || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_gold", 8), speed: G.readAnimationSpeed("pawn_idle_gold", "normal") };
            return { sprite: sprites.pawn_idle_wood || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_wood", 8), speed: G.readAnimationSpeed("pawn_idle_wood", "normal") };
        }

        // ── Archer (playable, Blue) ─────────────────────────────────────
        if (npc.kind === "archer") {
            if (state === "MOVING" || state === "RETURNING") {
                return { sprite: sprites.archer_run, frames: G.readFrameCount("archer_run", 4), speed: G.readAnimationSpeed("archer_run", "fast") };
            }
            if (state === "PERFORMING") {
                if (actionType === "eat") {
                    return { sprite: sprites.archer_idle, frames: G.readFrameCount("archer_idle", 6), speed: G.readAnimationSpeed("archer_idle", "slow") };
                }
                // Shoot: only play shoot anim during fire phase, idle during aim
                if (npc.isFiring) {
                    return { sprite: sprites.archer_shoot, frames: G.readFrameCount("archer_shoot", 8), speed: G.readAnimationSpeed("archer_shoot", "fast") };
                }
                return { sprite: sprites.archer_idle, frames: G.readFrameCount("archer_idle", 6), speed: G.readAnimationSpeed("archer_idle", "normal") };
            }
            // IDLE / DONE
            return { sprite: sprites.archer_idle, frames: G.readFrameCount("archer_idle", 6), speed: G.readAnimationSpeed("archer_idle", "normal") };
        }

        // ── Pawn (default) ──────────────────────────────────────────────
        if (state === "MOVING") {
            switch (actionType) {
                case "chop_wood":  return { sprite: sprites.pawn_run_axe  || sprites.pawn_run, frames: G.readFrameCount("pawn_run_axe", 6), speed: G.readAnimationSpeed("pawn_run_axe", "fast") };
                case "mine_rock":  return { sprite: sprites.pawn_run_pick || sprites.pawn_run, frames: G.readFrameCount("pawn_run_pickaxe", 6), speed: G.readAnimationSpeed("pawn_run_pickaxe", "fast") };
                case "build":      return { sprite: sprites.pawn_run_ham  || sprites.pawn_run, frames: G.readFrameCount("pawn_run_hammer", 6), speed: G.readAnimationSpeed("pawn_run_hammer", "fast") };
                default:           return { sprite: sprites.pawn_run, frames: G.readFrameCount("pawn_run", 6), speed: G.readAnimationSpeed("pawn_run", "fast") };
            }
        }

        if (state === "PERFORMING") {
            switch (actionType) {
                case "chop_wood":
                    if (G.gameFrame % 20 === 0) G.spawnParticle("dust", npc.x, npc.y + 5);
                    return { sprite: sprites.pawn_act_axe,   frames: G.readFrameCount("pawn_interact_axe", 6),     speed: G.readAnimationSpeed("pawn_interact_axe", "fast") };
                case "mine_rock":
                    if (G.gameFrame % 18 === 0) G.spawnParticle("fire", npc.x, npc.y - 10);
                    return { sprite: sprites.pawn_act_pick,  frames: G.readFrameCount("pawn_interact_pickaxe", 6), speed: G.readAnimationSpeed("pawn_interact_pickaxe", "fast") };
                case "build":
                    if (G.gameFrame % 25 === 0) G.spawnParticle("dust", npc.x, npc.y + 5);
                    return { sprite: sprites.pawn_act_ham,   frames: G.readFrameCount("pawn_interact_hammer", 3),  speed: G.readAnimationSpeed("pawn_interact_hammer", "fast") };
                case "plant_wheat":
                case "collect_wheat":
                    return { sprite: sprites.pawn_act_knife, frames: G.readFrameCount("pawn_interact_knife", 6),   speed: G.readAnimationSpeed("pawn_interact_knife", "fast") };
                case "eat":
                    return { sprite: sprites.pawn_idle_meat, frames: G.readFrameCount("pawn_idle_meat", 8),        speed: G.readAnimationSpeed("pawn_idle_meat", "normal") };
                default:
                    return { sprite: sprites.pawn_idle,      frames: G.readFrameCount("pawn_idle", 8),             speed: G.readAnimationSpeed("pawn_idle", "normal") };
            }
        }

        switch (actionType) {
            case "chop_wood":  return { sprite: sprites.pawn_idle_axe  || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_axe", 8),     speed: G.readAnimationSpeed("pawn_idle_axe", "normal") };
            case "mine_rock":  return { sprite: sprites.pawn_idle_pick || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_pickaxe", 8), speed: G.readAnimationSpeed("pawn_idle_pickaxe", "normal") };
            case "build":      return { sprite: sprites.pawn_idle_ham  || sprites.pawn_idle, frames: G.readFrameCount("pawn_idle_hammer", 8),  speed: G.readAnimationSpeed("pawn_idle_hammer", "normal") };
            default:           return { sprite: sprites.pawn_idle,                       frames: G.readFrameCount("pawn_idle", 8),         speed: G.readAnimationSpeed("pawn_idle", "normal") };
        }
    }

    function drawNPC(ctx, npc, sx, sy) {
        const sprites = G.sprites;
        const rect = spriteRect(npc, sx, sy, G.mapCached.tileSize);
        const SIZE = rect.height;
        const HALF = SIZE / 2;
        const facingRight = G.updateFacing(npc);

        // Shadow
        if (sprites.shadow) {
            ctx.globalAlpha = 0.25;
            ctx.drawImage(sprites.shadow, 0, 0, SHADOW_SPRITE_SIZE, SHADOW_SPRITE_SIZE, sx - HALF * 0.7, sy - 4, SIZE * 0.7, SIZE * 0.35);
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
        const spriteDrawn = info.sprite && G.drawSpriteFrame(ctx, info.sprite, frame, info.frames,
            rect.left, rect.top, rect.width, rect.height, !facingRight);

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

    function getFaunaSpriteInfo(f) {
        const sprites = G.sprites;
        const state = f.state;

        if (f.kind === "cat") return null;  // cat uses individual frames

        // ── Wild Archer (Red) ───────────────────────────────────────────
        if (f.kind === "wild_archer") {
            if (state === "SHOOTING") {
                // Only play shoot anim during fire phase, idle during aim
                if (f.isFiring) {
                    return { sprite: sprites.red_archer_shoot, frames: G.readFrameCount("archer_shoot", 8), speed: G.readAnimationSpeed("archer_shoot", "fast") };
                }
                return { sprite: sprites.red_archer_idle, frames: G.readFrameCount("archer_idle", 6), speed: G.readAnimationSpeed("archer_idle", "normal") };
            }
            if (state === "WANDERING") {
                return { sprite: sprites.red_archer_run, frames: G.readFrameCount("archer_run", 4), speed: G.readAnimationSpeed("archer_run", "fast") };
            }
            // IDLE
            return { sprite: sprites.red_archer_idle, frames: G.readFrameCount("archer_idle", 6), speed: G.readAnimationSpeed("archer_idle", "normal") };
        }

        // ── Sheep ───────────────────────────────────────────────────────
        if (state === "GRAZING") {
            return {
                sprite: sprites.sheep_grass,
                frames: G.readFrameCount("sheep_grass", 12),
                speed: G.readAnimationSpeed("sheep_grass", "normal"),
            };
        }
        if (state === "WANDERING") {
            return {
                sprite: sprites.sheep_move,
                frames: G.readFrameCount("sheep_move", 4),
                speed: G.readAnimationSpeed("sheep_move", "normal"),
            };
        }
        // IDLE
        return {
            sprite: sprites.sheep_idle,
            frames: G.readFrameCount("sheep_idle", 6),
            speed: G.readAnimationSpeed("sheep_idle", "normal"),
        };
    }

    function drawFauna(ctx, f, sx, sy) {
        if (f.kind === "cat") {
            drawCat(ctx, f, sx, sy);
            return;
        }

        if (f.kind === "wild_archer") {
            drawWildArcher(ctx, f, sx, sy);
            return;
        }

        const sprites = G.sprites;
        const rect = spriteRect(f, sx, sy, G.mapCached.tileSize);
        const SIZE = rect.height;
        const HALF = SIZE / 2;
        const facingRight = G.updateFacing(f);

        // Shadow
        if (sprites.shadow) {
            ctx.globalAlpha = 0.2;
            ctx.drawImage(sprites.shadow, 0, 0, SHADOW_SPRITE_SIZE, SHADOW_SPRITE_SIZE, sx - HALF * 0.6, sy - 2, SIZE * 0.6, SIZE * 0.25);
            ctx.globalAlpha = 1;
        } else {
            ctx.fillStyle = "rgba(0,0,0,0.18)";
            ctx.beginPath(); ctx.ellipse(sx, sy, HALF * 0.5, HALF * 0.2, 0, 0, Math.PI * 2); ctx.fill();
        }

        // Sprite
        const info = getFaunaSpriteInfo(f);
        const frame = G.spriteFrame(info.frames, info.speed, f.id);
        const spriteDrawn = info.sprite && G.drawSpriteFrame(ctx, info.sprite, frame, info.frames,
            rect.left, rect.top, rect.width, rect.height, !facingRight);

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
        const sprites = G.sprites;
        const rect = spriteRect(f, sx, sy, G.mapCached.tileSize);
        const SIZE = rect.height;
        const HALF = SIZE / 2;

        // Shadow
        if (sprites.shadow) {
            ctx.globalAlpha = 0.2;
            ctx.drawImage(sprites.shadow, 0, 0, SHADOW_SPRITE_SIZE, SHADOW_SPRITE_SIZE, sx - HALF * 0.5, sy - 2, SIZE * 0.5, SIZE * 0.2);
            ctx.globalAlpha = 1;
        }

        // Pick the right frame from the individual images
        const fi = Math.floor(G.gameFrame / CAT_ANIMATION_INTERVAL) % G.catFrameCount;
        const frameImg = sprites["cat_" + fi];
        if (frameImg) {
            ctx.drawImage(frameImg, rect.left, rect.top, rect.width, rect.height);
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

    // ── Draw Wild Archer (Red team, fauna) ──────────────────────────────

    function drawWildArcher(ctx, f, sx, sy) {
        const sprites = G.sprites;
        const rect = spriteRect(f, sx, sy, G.mapCached.tileSize);
        const SIZE = rect.height;
        const HALF = SIZE / 2;
        const facingRight = G.updateFacing(f);

        // Shadow
        if (sprites.shadow) {
            ctx.globalAlpha = 0.25;
            ctx.drawImage(sprites.shadow, 0, 0, SHADOW_SPRITE_SIZE, SHADOW_SPRITE_SIZE, sx - HALF * 0.7, sy - 4, SIZE * 0.7, SIZE * 0.35);
            ctx.globalAlpha = 1;
        } else {
            ctx.fillStyle = "rgba(0,0,0,0.25)";
            ctx.beginPath(); ctx.ellipse(sx, sy, HALF * 0.6, HALF * 0.25, 0, 0, Math.PI * 2); ctx.fill();
        }

        // Sprite
        const info = getFaunaSpriteInfo(f);
        const frame = G.spriteFrame(info.frames, info.speed, f.id);
        const spriteDrawn = info.sprite && G.drawSpriteFrame(ctx, info.sprite, frame, info.frames,
            rect.left, rect.top, rect.width, rect.height, !facingRight);

        if (!spriteDrawn) {
            // Fallback: red circle
            ctx.fillStyle = "#c62828";
            ctx.beginPath(); ctx.arc(sx, sy - 14, 14, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "#b71c1c"; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(sx, sy - 14, 14, 0, Math.PI * 2); ctx.stroke();
        }

        // Name (red tint)
        ctx.font = "bold 11px Consolas"; ctx.textAlign = "center";
        ctx.fillStyle = "rgba(0,0,0,0.7)"; ctx.fillText(f.name, sx + 1, sy - SIZE + 4);
        ctx.fillStyle = "#ff8a80"; ctx.fillText(f.name, sx, sy - SIZE + 3);

        // State
        ctx.font = "9px Consolas"; ctx.fillStyle = "#ffab91";
        ctx.fillText(f.state, sx, sy - SIZE + 14);

        // HP bar
        if (f.health < f.maxHealth) {
            drawBar(ctx, sx, sy - SIZE - 2, 28, 4, f.health / f.maxHealth, "#ef5350");
        }
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
