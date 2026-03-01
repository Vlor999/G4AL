/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – UI Updates, Speech Bubbles & Modals
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // ── DOM UI update (called every frame from render loop) ─────────────

    G.updateUI = function () {
        if (!G.gameState) return;

        // Resources
        document.getElementById("res-wood").textContent = G.gameState.storage.wood || 0;
        document.getElementById("res-stone").textContent = G.gameState.storage.stone || 0;
        document.getElementById("res-gold").textContent = G.gameState.storage.gold || 0;
        document.getElementById("res-wheat").textContent = G.gameState.storage.wheat || 0;

        // Selection panel
        const sel = G.gameState.npcs.find(n => n.id === G.selectedId);
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
            btn.disabled = !G.selectedId;
        });

        // Roster
        const rosterEl = document.getElementById("roster-list");
        const rosterHTML = G.gameState.npcs.map(n => {
            const cls = n.selected ? "roster-entry selected" : "roster-entry";
            const marker = n.selected ? "\u25b8 " : "  ";
            return `<div class="${cls}" data-npc-id="${n.id}">${marker}${n.name}<span class="state-badge">${n.state}</span></div>`;
        }).join("");
        if (rosterEl.innerHTML !== rosterHTML) rosterEl.innerHTML = rosterHTML;

        // Log
        const logEl = document.getElementById("log-messages");
        const logHTML = G.gameState.log.map(m => `<div class="log-entry">${escapeHtml(m)}</div>`).join("");
        if (logEl.dataset.last !== logHTML) {
            logEl.innerHTML = logHTML;
            logEl.scrollTop = logEl.scrollHeight;
            logEl.dataset.last = logHTML;
        }
    };

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Speech Bubbles ──────────────────────────────────────────────────

    G.updateSpeechBubbles = function () {
        const container = document.getElementById("canvas-container");

        // Remove stale bubbles
        container.querySelectorAll(".speech-bubble").forEach(el => el.remove());

        if (!G.gameState) return;
        for (const npc of G.gameState.npcs) {
            if (!npc.speechText) continue;
            const sx = npc.x - G.camX;
            const sy = npc.y - G.camY - 70;
            if (sx < -100 || sx > G.canvas.width + 100 || sy < -100) continue;

            const bubble = document.createElement("div");
            bubble.className = "speech-bubble";
            bubble.textContent = npc.speechText;
            bubble.style.left = sx + "px";
            bubble.style.top = sy + "px";
            container.appendChild(bubble);
        }
    };

    // ═══════════════════════════════════════════════════════════════════════
    //  Modals
    // ═══════════════════════════════════════════════════════════════════════

    // ── Mic Permission Modal ────────────────────────────────────────────

    const micModal = document.getElementById("mic-modal");
    const micBtn = document.getElementById("mic-allow-btn");
    const micCloseBtn = document.getElementById("mic-close-btn");

    if (micModal && micBtn) {
        micBtn.addEventListener("click", async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(t => t.stop());
                micBtn.textContent = "[MIC AUTHORIZED]";
                micBtn.classList.add("granted");
                setTimeout(() => { micModal.classList.add("hidden"); }, 600);
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

        micModal.addEventListener("click", (e) => {
            if (e.target === micModal) micModal.classList.add("hidden");
        });
    }

    // ── Team Information Modal ──────────────────────────────────────────

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

        teamModal.addEventListener("click", (e) => {
            if (e.target === teamModal) teamModal.classList.add("hidden");
        });
    }

    // ── Guide Modal (page-turning help) ─────────────────────────────────

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

})(window.G4AL);
