/* ═══════════════════════════════════════════════════════════════════════════
   G4AL Web Client – Canvas Renderer + WebSocket + Push-to-Talk
   ═══════════════════════════════════════════════════════════════════════════ */

(() => {
"use strict";

// ── Constants ───────────────────────────────────────────────────────────
const CAMERA_SPEED  = 10;        // px per frame when scrolling
const API = "";                  // same origin

// ── Tile colors (matching Python settings) ──────────────────────────────
const TILE_COLORS = {
    0: { light: "#7cb342", dark: "#689f38" },   // GRASS
    1: { light: "#a18864", dark: "#a18864" },   // DIRT
    2: { light: "#dcc88c", dark: "#dcc88c" },   // SAND
    3: { light: "#42a5f5", dark: "#42a5f5" },   // WATER
};

// ── State ───────────────────────────────────────────────────────────────
let gameState  = null;       // latest from server
let mapCached  = null;       // {cols, rows, tileSize, tiles} – only changes on load
let selectedId = null;       // currently selected NPC id

// Camera
let camX = 0, camY = 0;
const keysDown = new Set();

// Canvas refs
const canvas    = document.getElementById("game-canvas");
const ctx       = canvas.getContext("2d");
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
});

// ── Resize canvas to fill container ─────────────────────────────────────
function resizeCanvas() {
    canvas.width  = container.clientWidth;
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

let pttRecording   = false;
let pttMediaStream = null;
let pttRecorder    = null;
let pttChunks      = [];

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
            } catch(e) { console.error("PTT upload failed:", e); }
        };

        pttRecorder.start();
    } catch(e) {
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
    const view   = new DataView(buffer);

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
//  Map rendering (pre-rendered to offscreen canvas)
// ═══════════════════════════════════════════════════════════════════════════

let mapCanvas = null;

function buildMapImage() {
    if (!mapCached) return;
    const { cols, rows, tileSize, tiles } = mapCached;
    mapCanvas = document.createElement("canvas");
    mapCanvas.width  = cols * tileSize;
    mapCanvas.height = rows * tileSize;
    const mctx = mapCanvas.getContext("2d");

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const tt = tiles[r][c];
            const colors = TILE_COLORS[tt] || TILE_COLORS[0];
            const color = (r + c) % 2 === 0 ? colors.light : colors.dark;
            mctx.fillStyle = color;
            mctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
            // subtle grid
            mctx.strokeStyle = darken(color, 15);
            mctx.lineWidth = 1;
            mctx.strokeRect(c * tileSize, r * tileSize, tileSize, tileSize);
        }
    }
}

function darken(hex, amount) {
    const r = Math.max(0, parseInt(hex.slice(1,3),16) - amount);
    const g = Math.max(0, parseInt(hex.slice(3,5),16) - amount);
    const b = Math.max(0, parseInt(hex.slice(5,7),16) - amount);
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

    // ── Camera update ───────────────────────────────────────────────
    updateCamera(W, H);

    // ── Map ─────────────────────────────────────────────────────────
    if (mapCanvas) {
        ctx.drawImage(mapCanvas, -camX, -camY);
    }

    // ── Resources ───────────────────────────────────────────────────
    const ts = mapCached.tileSize;
    for (const res of gameState.resources) {
        const sx = res.col * ts + ts / 2 - camX;
        const sy = res.row * ts + ts / 2 - camY;

        // Cull off-screen
        if (sx < -ts || sx > W + ts || sy < -ts || sy > H + ts) continue;

        drawResource(ctx, res, sx, sy, ts);
    }

    // ── NPCs (sorted by y for depth) ────────────────────────────────
    const npcs = [...gameState.npcs].sort((a, b) => a.y - b.y);
    for (const npc of npcs) {
        const sx = npc.x - camX;
        const sy = npc.y - camY;
        if (sx < -40 || sx > W + 40 || sy < -40 || sy > H + 40) continue;
        drawNPC(ctx, npc, sx, sy);
    }

    // ── UI overlay updates ──────────────────────────────────────────
    updateUI();
    updateSpeechBubbles();

    requestAnimationFrame(render);
}

// ── Draw resource ───────────────────────────────────────────────────────

function drawResource(ctx, res, sx, sy, ts) {
    const half = ts / 2 - 4;

    switch (res.kind) {
        case "tree":
            // Trunk
            ctx.fillStyle = "#795b3d";
            ctx.fillRect(sx - 4, sy - 2, 8, 16);
            // Leaves
            ctx.fillStyle = "#388e3c";
            ctx.beginPath();
            ctx.arc(sx, sy - 10, 18, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "#4caf50";
            ctx.beginPath();
            ctx.arc(sx - 3, sy - 14, 13, 0, Math.PI * 2);
            ctx.fill();
            break;

        case "rock":
            ctx.fillStyle = res.hasGold ? "#9e9e9e" : "#757575";
            ctx.beginPath();
            ctx.ellipse(sx, sy, 16, 12, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "#616161";
            ctx.beginPath();
            ctx.ellipse(sx, sy, 12, 9, 0, 0, Math.PI * 2);
            ctx.fill();
            if (res.hasGold) {
                ctx.fillStyle = "#ffd700";
                [[-5,-2],[3,1],[-1,4]].forEach(([dx,dy]) => {
                    ctx.beginPath();
                    ctx.arc(sx+dx, sy+dy, 2.5, 0, Math.PI*2);
                    ctx.fill();
                });
            }
            break;

        case "structure":
            if (res.built) {
                // Built house
                ctx.fillStyle = "#654321";
                ctx.fillRect(sx - 20, sy - 20, 40, 40);
                ctx.strokeStyle = "#503018";
                ctx.lineWidth = 2;
                ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                // Roof
                ctx.fillStyle = "#b22222";
                ctx.beginPath();
                ctx.moveTo(sx - 24, sy - 20);
                ctx.lineTo(sx + 24, sy - 20);
                ctx.lineTo(sx, sy - 38);
                ctx.closePath();
                ctx.fill();
            } else {
                // Under construction
                ctx.fillStyle = "#8b7765";
                ctx.fillRect(sx - 20, sy - 20, 40, 40);
                ctx.strokeStyle = "#50403c";
                ctx.lineWidth = 2;
                ctx.strokeRect(sx - 20, sy - 20, 40, 40);
                drawBar(ctx, sx, sy - 26, 36, 5, res.buildProgress / 100, "#4caf50");
            }
            break;

        case "wheat": {
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
        drawBar(ctx, sx, sy - 26, 30, 5, res.hp / res.maxHp, "#4caf50");
    }
}

// ── Draw NPC ────────────────────────────────────────────────────────────

function drawNPC(ctx, npc, sx, sy) {
    const R = 14;
    const bob = npc.state === "IDLE" ? Math.sin(Date.now() / 200) * 2 : 0;
    const by = sy + bob;

    // Shadow
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.beginPath();
    ctx.ellipse(sx, sy + R - 2, R, R / 2, 0, 0, Math.PI * 2);
    ctx.fill();

    // Selection ring
    if (npc.selected) {
        ctx.strokeStyle = "#00e676";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, by, R + 4, 0, Math.PI * 2);
        ctx.stroke();
    }

    // Body
    ctx.fillStyle = "#ffb74d";
    ctx.beginPath();
    ctx.arc(sx, by, R, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = npc.selected ? "#00e676" : "#e6801e";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(sx, by, R, 0, Math.PI * 2);
    ctx.stroke();

    // Eyes
    ctx.fillStyle = "#333";
    ctx.beginPath();
    ctx.arc(sx - 4, by - 3, 2, 0, Math.PI * 2);
    ctx.arc(sx + 4, by - 3, 2, 0, Math.PI * 2);
    ctx.fill();

    // Name label
    ctx.font = "bold 12px Consolas";
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillText(npc.name, sx + 1, by - R - 16);
    ctx.fillStyle = "#fff";
    ctx.fillText(npc.name, sx, by - R - 17);

    // State label
    ctx.font = "10px Consolas";
    ctx.fillStyle = "#ccc";
    ctx.fillText(npc.state, sx, by - R - 5);

    // HP bar (only when damaged)
    if (npc.health < npc.maxHealth) {
        drawBar(ctx, sx, by - R - 30, 28, 4, npc.health / npc.maxHealth, "#4caf50");
    }

    // Hunger bar (always visible)
    const hungerRatio = npc.hunger / npc.maxHunger;
    const hungerColor = hungerRatio > 0.25 ? "#ff9800" : "#f44336";
    drawBar(ctx, sx, sy + R + 4, 24, 4, hungerRatio, hungerColor);
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
    document.getElementById("res-wood").textContent  = gameState.storage.wood  || 0;
    document.getElementById("res-stone").textContent = gameState.storage.stone || 0;
    document.getElementById("res-gold").textContent  = gameState.storage.gold  || 0;
    document.getElementById("res-wheat").textContent = gameState.storage.wheat || 0;

    // Selection panel
    const sel = gameState.npcs.find(n => n.id === selectedId);
    const placeholder = document.getElementById("sel-placeholder");
    const details = document.getElementById("sel-details");
    if (sel) {
        placeholder.style.display = "none";
        details.style.display = "block";
        document.getElementById("sel-name").textContent = sel.name;
        document.getElementById("sel-hp-text").textContent = `${Math.round(sel.health)}/${sel.maxHealth}`;
        document.getElementById("sel-hp-bar").style.width = `${(sel.health / sel.maxHealth) * 100}%`;
        document.getElementById("sel-hunger-text").textContent = `${Math.round(sel.hunger)}%`;
        const hungerBar = document.getElementById("sel-hunger-bar");
        hungerBar.style.width = `${(sel.hunger / sel.maxHunger) * 100}%`;
        hungerBar.classList.toggle("low", sel.hunger / sel.maxHunger < 0.25);
        document.getElementById("sel-state").textContent = sel.state;
    } else {
        placeholder.style.display = "block";
        details.style.display = "none";
    }

    // Action buttons
    document.querySelectorAll(".action-btn").forEach(btn => {
        btn.disabled = !selectedId;
    });

    // Roster
    const rosterEl = document.getElementById("roster-list");
    const rosterHTML = gameState.npcs.map(n => {
        const cls = n.selected ? "roster-entry selected" : "roster-entry";
        const marker = n.selected ? "▸ " : "  ";
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
        const sy = npc.y - camY - 40;
        if (sx < -100 || sx > canvas.width + 100 || sy < -100) continue;

        const bubble = document.createElement("div");
        bubble.className = "speech-bubble";
        bubble.textContent = npc.speechText;
        bubble.style.left = sx + "px";
        bubble.style.top  = sy + "px";
        container.appendChild(bubble);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Input handling
// ═══════════════════════════════════════════════════════════════════════════

// Keyboard (camera scrolling + push-to-talk)
document.addEventListener("keydown", e => {
    // Don't capture keys when typing in command input
    if (document.activeElement === document.getElementById("command-input")) return;
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

    // Try to click on an NPC
    let clicked = null;
    for (const npc of gameState.npcs) {
        const dx = wx - npc.x;
        const dy = wy - npc.y;
        if (Math.sqrt(dx*dx + dy*dy) <= 18) {
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

// Command input
document.getElementById("command-input").addEventListener("keydown", e => {
    if (e.key === "Enter") {
        const input = e.target;
        const text = input.value.trim();
        if (text) {
            postJSON("/api/command", { text });
            input.value = "";
        }
    }
    if (e.key === "Escape") {
        e.target.blur();
    }
    e.stopPropagation(); // prevent camera from moving
});

// ═══════════════════════════════════════════════════════════════════════════
//  Boot
// ═══════════════════════════════════════════════════════════════════════════

// Start render loop (state arrives via WebSocket)
requestAnimationFrame(render);

})();
