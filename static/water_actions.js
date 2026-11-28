/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – NPCs at the lake: facing the water while fishing, drawn clipped at the
   waterline while swimming, and a splash on each water event. The state says
   where the water is (`waterTile`) and whether the NPC is in it (`isInWater`);
   only the previous values per NPC are kept here, to see the events.
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // Share of the sprite height, from its top, still drawn above the waterline.
    const WATERLINE_RATIO = 0.62;

    // Per NPC id: { isInWater, isFishing, waterTile } of the previous render frame.
    const previousByNpcId = {};

    function isFishing(npc) {
        return npc.state === "PERFORMING" && npc.actionType === "fish";
    }

    function isSwimming(npc) {
        return npc.state === "PERFORMING" && npc.actionType === "swim";
    }

    function tileCenter(tile) {
        const ts = G.mapCached.tileSize;
        return { x: tile[0] * ts + ts / 2, y: tile[1] * ts + ts / 2 };
    }

    /** Splash where an NPC enters or leaves the water, and on the catch that ends a fishing. */
    G.spawnWaterSplashes = function (npcs) {
        const liveIds = new Set(npcs.map(npc => String(npc.id)));
        for (const id of Object.keys(previousByNpcId)) {
            if (!liveIds.has(id)) delete previousByNpcId[id];
        }
        for (const npc of npcs) {
            const previous = previousByNpcId[npc.id];
            const current = { isInWater: npc.isInWater, isFishing: isFishing(npc), waterTile: npc.waterTile };
            previousByNpcId[npc.id] = current;
            if (!previous) continue;
            if (previous.isInWater !== current.isInWater) {
                G.spawnParticle("splash", npc.x, npc.y);
            } else if (previous.isFishing && !current.isFishing && previous.waterTile) {
                const water = tileCenter(previous.waterTile);
                G.spawnParticle("splash", water.x, water.y);
            }
        }
    };

    /** Facing of an NPC fishing or swimming: towards its water tile when it lies east or
        west. While it walks, its movement decides (`facingRight`). */
    G.faceWater = function (npc, facingRight) {
        if (!npc.waterTile || !(isFishing(npc) || isSwimming(npc))) return facingRight;
        const npcCol = Math.floor(npc.x / G.mapCached.tileSize);
        if (npc.waterTile[0] > npcCol) return true;
        if (npc.waterTile[0] < npcCol) return false;
        return facingRight;
    };

    /** Clip the next drawing to the part of the sprite rectangle above the waterline when the
        NPC is in the water; returns whether a clip was set, to undo with `ctx.restore()`. */
    G.clipAtWaterline = function (ctx, npc, rect) {
        if (!npc.isInWater) return false;
        ctx.save();
        ctx.beginPath();
        ctx.rect(rect.left, rect.top, rect.width, rect.height * WATERLINE_RATIO);
        ctx.clip();
        return true;
    };

})(window.G4AL);
