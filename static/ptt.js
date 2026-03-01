/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Push-to-Talk Recording & WAV Conversion
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    let pttRecording = false;
    let pttMediaStream = null;
    let pttRecorder = null;
    let pttChunks = [];

    /** Show / hide the recording indicator */
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

    G.pttStart = async function () {
        if (pttRecording) return;
        pttRecording = true;
        pttChunks = [];
        setPttIndicator(true);

        try {
            pttMediaStream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
            });

            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "";
            pttRecorder = new MediaRecorder(pttMediaStream, mimeType ? { mimeType } : {});

            pttRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) pttChunks.push(e.data);
            };

            pttRecorder.onstop = async () => {
                setPttIndicator(false);
                pttMediaStream.getTracks().forEach(t => t.stop());
                if (pttChunks.length === 0) return;

                const blob = new Blob(pttChunks, { type: pttRecorder.mimeType });
                const wavBlob = await blobToWav(blob);

                const form = new FormData();
                form.append("audio", wavBlob, "recording.wav");
                try {
                    await fetch("/api/audio", { method: "POST", body: form });
                } catch (e) { console.error("PTT upload failed:", e); }
            };

            pttRecorder.start();
        } catch (e) {
            console.error("Mic access denied or unavailable:", e);
            pttRecording = false;
            setPttIndicator(false);
        }
    };

    G.pttStop = function () {
        if (!pttRecording || !pttRecorder) return;
        pttRecording = false;
        if (pttRecorder.state === "recording") {
            pttRecorder.stop();
        }
    };

    /**
     * Convert an audio Blob to 16-bit PCM WAV via AudioContext.
     */
    async function blobToWav(blob) {
        const arrayBuf = await blob.arrayBuffer();
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        let audioBuf;
        try {
            audioBuf = await audioCtx.decodeAudioData(arrayBuf);
        } catch {
            audioCtx.close();
            return blob;
        }
        audioCtx.close();

        const samples = audioBuf.getChannelData(0);
        const numSamples = samples.length;

        const buffer = new ArrayBuffer(44 + numSamples * 2);
        const view = new DataView(buffer);

        function writeStr(offset, str) {
            for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
        }
        writeStr(0, "RIFF");
        view.setUint32(4, 36 + numSamples * 2, true);
        writeStr(8, "WAVE");
        writeStr(12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, 16000, true);
        view.setUint32(28, 32000, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeStr(36, "data");
        view.setUint32(40, numSamples * 2, true);

        let offset = 44;
        for (let i = 0; i < numSamples; i++) {
            let s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            offset += 2;
        }

        return new Blob([buffer], { type: "audio/wav" });
    }

})(window.G4AL);
