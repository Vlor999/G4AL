/* ═══════════════════════════════════════════════════════════════════════════
   G4AL – Particle effects: short-lived dust and fire drawn over
   the world. View state only: the server sends no particle.
   ═══════════════════════════════════════════════════════════════════════════ */

(function (G) {
    "use strict";

    // Pixels past the canvas edges where a particle is still drawn.
    const PARTICLE_OFFSCREEN_MARGIN = 64;
    // Render frames a particle lives, by type.
    const PARTICLE_LIFE = { dust: 30, fire: 40 };

    const particles = [];

    G.spawnParticle = function (type, wx, wy) {
        particles.push({ type, wx, wy, birth: G.gameFrame, life: PARTICLE_LIFE[type] });
    };

    /** Draw every live particle and drop the ones whose life has run out. */
    G.drawParticles = function (ctx, W, H) {
        const sprites = G.sprites;
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            const age = G.gameFrame - p.birth;
            if (age >= p.life) { particles.splice(i, 1); continue; }
            const progress = age / p.life;
            const px = p.wx - G.camX;
            const py = p.wy - G.camY;
            if (px < -PARTICLE_OFFSCREEN_MARGIN || px > W + PARTICLE_OFFSCREEN_MARGIN || py < -PARTICLE_OFFSCREEN_MARGIN || py > H + PARTICLE_OFFSCREEN_MARGIN) continue;
            ctx.globalAlpha = 1 - progress;
            if (p.type === "dust") {
                const ds = sprites.dust1 || sprites.dust2;
                if (ds) {
                    const dustFrames = G.readFrameCount("dust_1", 8);
                    const fi = G.spriteFrame(dustFrames, G.readAnimationSpeed("dust_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, ds, fi, dustFrames, px - 24, py - 24, 48, 48, false);
                }
            } else if (p.type === "fire") {
                const fs = sprites.fire1 || sprites.fire2;
                if (fs) {
                    const fireFrames = G.readFrameCount("fire_1", 8);
                    const fi = G.spriteFrame(fireFrames, G.readAnimationSpeed("fire_1", "fast"), p.birth);
                    G.drawSpriteFrame(ctx, fs, fi, fireFrames, px - 16, py - 32, 32, 32, false);
                }
            }
            ctx.globalAlpha = 1;
        }
    };

})(window.G4AL);
