/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Chat panel: typed orders out, the player's commands and the NPCs'
   voice lines in (the state's "chat" list, docs/api.md), and the model picker
   (the state's "models" and "selectedModelId")
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    const modelSelect = document.getElementById("model-select");

    chatForm.addEventListener("submit", event => {
        event.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;
        chatInput.value = "";
        G.postJSON("/api/command", { text });
    });

    modelSelect.addEventListener("change", () => {
        G.postJSON("/api/model", { modelId: modelSelect.value });
    });

    function renderModelOption(model) {
        const voiceMark = model.hasVoiceInput ? " \ud83c\udfa4" : "";
        return `<option value="${G.escapeHtml(model.id)}">${G.escapeHtml(model.name)}${voiceMark}</option>`;
    }

    function updateModelPicker() {
        const optionsHTML = G.gameState.models.map(renderModelOption).join("");
        if (modelSelect.dataset.last !== optionsHTML) {
            modelSelect.innerHTML = optionsHTML;
            modelSelect.dataset.last = optionsHTML;
        }
        // While the list is open, the state pushed every ~50 ms must not undo the pick.
        if (document.activeElement !== modelSelect) {
            modelSelect.value = G.gameState.selectedModelId;
        }
    }

    function renderChatMessage(message) {
        switch (message.kind) {
            case "typed_command":
                return `<div class="chat-message chat-command">&gt; ${G.escapeHtml(message.text)}</div>`;
            case "spoken_command":
                return `<div class="chat-message chat-command">&gt; 🎤 voice command</div>`;
            case "voice_line":
                return `<div class="chat-message chat-voice-line"><span class="chat-npc-name">${G.escapeHtml(message.npcName)}</span> ${G.escapeHtml(message.text)}</div>`;
            default:
                return "";
        }
    }

    G.updateChat = function () {
        updateModelPicker();
        const chatHTML = G.gameState.chat.map(renderChatMessage).join("");
        if (chatMessages.dataset.last === chatHTML) return;
        chatMessages.innerHTML = chatHTML;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        chatMessages.dataset.last = chatHTML;
    };

})(window.G4AL);
