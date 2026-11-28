/* Client entry point: camera, Socket.IO state updates, boot. index.html loads it last,
   once every other script has added its functions to window.G4AL. */

(function (G) {
    "use strict";

    const CAMERA_SPEED = 10;

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

    let cameraCentered = false;
    const socket = io();

    socket.on("state", (data) => {
        G.gameState = data;

        // The map never changes during a game, so its image is built once.
        if (!G.mapCached && G.gameState.map) {
            G.mapCached = G.gameState.map;
            G.buildMapImage();
        }

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

    G.loadAllSprites().then(() => {
        if (G.mapCached) G.buildMapImage();
    });

    requestAnimationFrame(G.render);

})(window.G4AL);
