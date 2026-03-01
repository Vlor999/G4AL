/* ═══════════════════════════════════════════════════════════════════════════
   G4AL SoundManager – Simple background music player
   ═══════════════════════════════════════════════════════════════════════════
   Plays a single looping background track (calm.mp3) with one volume control.
   Handles Browser Autoplay Policy by deferring playback until first user
   interaction (click / keydown).
   ═══════════════════════════════════════════════════════════════════════════ */

class SoundManager {
    constructor() {
        this._audio = new Audio("/static/audio/music/calm.mp3");
        this._audio.loop = true;
        this._audio.volume = 0.5;
        this._started = false;

        // Unlock on first user gesture (autoplay policy)
        this._boundUnlock = this._unlock.bind(this);
        document.addEventListener("click", this._boundUnlock);
        document.addEventListener("keydown", this._boundUnlock);
    }

    _unlock() {
        if (this._started) return;
        this._started = true;
        document.removeEventListener("click", this._boundUnlock);
        document.removeEventListener("keydown", this._boundUnlock);
        this._audio.play().catch(() => {});
    }

    /** Volume (0-1) */
    get volume() { return this._audio.volume; }
    set volume(v) { this._audio.volume = Math.max(0, Math.min(1, v)); }
}
