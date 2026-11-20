/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Input Handling (Keyboard, Mouse, Roster, Action Buttons)
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // ── Keyboard (camera scrolling + push-to-talk) ──────────────────────

    const CAMERA_ARROW_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]);

    // Keys typed in the chat input are text, not camera moves or push-to-talk.
    function isTypingInChat(e) {
        return e.target === document.getElementById("chat-input");
    }

    function isTypingInField(target) {
        return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
    }

    function hasVoiceInput() {
        return Boolean(G.gameState && G.gameState.hasVoiceInput);
    }

    document.addEventListener("keydown", e => {
        if (isTypingInChat(e)) return;
        // Arrows move the camera; left to the browser they also scroll the
        // panels, which on narrow screens scrolls the whole stacked page.
        if (CAMERA_ARROW_KEYS.has(e.key) && !isTypingInField(e.target)) {
            e.preventDefault();
        }
        G.keysDown.add(e.key);

        // G key = push-to-talk
        if ((e.key === "g" || e.key === "G") && !e.repeat && hasVoiceInput()) {
            G.pttStart();
        }
    });

    document.addEventListener("keyup", e => {
        G.keysDown.delete(e.key);
        if (e.key === "g" || e.key === "G") {
            G.pttStop();
        }
    });

    // ── Left click → select NPC ─────────────────────────────────────────

    G.canvas.addEventListener("click", e => {
        if (!G.gameState || !G.mapCached) return;
        const rect = G.canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const wx = mx + G.camX;
        const wy = my + G.camY;

        // Only select controllable entities (pawns), not fauna
        let clicked = null;
        for (const npc of G.gameState.npcs) {
            if (!npc.controllable) continue;
            const dx = wx - npc.x;
            const dy = wy - npc.y;
            if (Math.sqrt(dx * dx + dy * dy) <= 30) {
                clicked = npc;
                break;
            }
        }

        if (clicked) {
            G.selectedId = clicked.id;
            G.postJSON("/api/select", { npcId: clicked.id });
        } else {
            G.selectedId = null;
            G.postJSON("/api/select", {});
        }
    });

    // ── Right click → move selected NPC ─────────────────────────────────

    G.canvas.addEventListener("contextmenu", e => {
        e.preventDefault();
        if (!G.selectedId || !G.mapCached) return;
        const rect = G.canvas.getBoundingClientRect();
        const wx = (e.clientX - rect.left) + G.camX;
        const wy = (e.clientY - rect.top) + G.camY;
        const col = Math.floor(wx / G.mapCached.tileSize);
        const row = Math.floor(wy / G.mapCached.tileSize);
        G.postJSON("/api/move", { npcId: G.selectedId, col, row });
    });

    // ── Roster click → select NPC ───────────────────────────────────────

    document.getElementById("roster-list").addEventListener("click", e => {
        const entry = e.target.closest("[data-npc-id]");
        if (!entry) return;
        const id = parseInt(entry.dataset.npcId);
        G.selectedId = id;
        G.postJSON("/api/select", { npcId: id });
    });

    // ── Action buttons ──────────────────────────────────────────────────

    document.getElementById("action-buttons").addEventListener("click", e => {
        const btn = e.target.closest(".action-btn");
        if (!btn || !G.selectedId) return;
        const action = btn.dataset.action;
        G.postJSON("/api/action", { npcId: G.selectedId, action });
    });

})(window.G4AL);
