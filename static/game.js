/* ═══════════════════════════════════════════════════════════════════════════
   G4AL Web Client – Main Entry Point
   Shared state, Socket.IO, Camera, Canvas setup, Boot
   ═══════════════════════════════════════════════════════════════════════════
   Module load order (set in index.html):
     details.js → sprites.js → renderer.js → ptt.js → ui.js → input.js → game.js
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // ── Constants ───────────────────────────────────────────────────────
    const CAMERA_SPEED = 10;

    // ── Camera ──────────────────────────────────────────────────────────
    G.updateCamera = function (W, H) {
        if (!G.mapCached) return;
        const maxX = G.mapCached.cols * G.mapCached.tileSize - W;
        const maxY = G.mapCached.rows * G.mapCached.tileSize - H;

        if (G.keysDown.has("ArrowLeft")  || G.keysDown.has("a")) G.camX -= CAMERA_SPEED;
        if (G.keysDown.has("ArrowRight") || G.keysDown.has("d")) G.camX += CAMERA_SPEED;
        if (G.keysDown.has("ArrowUp")    || G.keysDown.has("w")) G.camY -= CAMERA_SPEED;
        if (G.keysDown.has("ArrowDown")  || G.keysDown.has("s")) G.camY += CAMERA_SPEED;

        G.camX = Math.max(0, Math.min(G.camX, maxX));
        G.camY = Math.max(0, Math.min(G.camY, maxY));
    };

    // ── Socket.IO connection ────────────────────────────────────────────
    let cameraCentered = false;
    const socket = io();

    socket.on("state", (data) => {
        G.gameState = data;

        // Cache map on first state
        if (!G.mapCached && G.gameState.map) {
            G.mapCached = G.gameState.map;
            G.buildMapImage();
        }

        // Center camera on first NPC once
        if (!cameraCentered && G.mapCached && G.gameState.npcs && G.gameState.npcs.length > 0) {
            const npc = G.gameState.npcs[0];
            const W = G.canvas.width  || G.container.clientWidth;
            const H = G.canvas.height || G.container.clientHeight;
            const maxX = G.mapCached.cols * G.mapCached.tileSize - W;
            const maxY = G.mapCached.rows * G.mapCached.tileSize - H;
            G.camX = Math.max(0, Math.min(npc.x - W / 2, maxX));
            G.camY = Math.max(0, Math.min(npc.y - H / 2, maxY));
            cameraCentered = true;
        }
    });

    // ── Boot: load sprites then start render loop ───────────────────────
    G.loadAllSprites().then(() => {
        if (G.mapCached) G.buildMapImage();
    });

    requestAnimationFrame(G.render);

})(window.G4AL);
