/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Chat panel: typed orders out, the player's commands and the NPCs'
   voice lines in (the state's "chat" list, docs/api.md)
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");

    chatForm.addEventListener("submit", event => {
        event.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;
        chatInput.value = "";
        G.postJSON("/api/command", { text });
    });

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
        const chatHTML = G.gameState.chat.map(renderChatMessage).join("");
        if (chatMessages.dataset.last === chatHTML) return;
        chatMessages.innerHTML = chatHTML;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        chatMessages.dataset.last = chatHTML;
    };

})(window.G4AL);
