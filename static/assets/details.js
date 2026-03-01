const SPRITE_CONFIG = {
    // === ENTITÉS ANIMÉES (Saut de frame) ===
    trees: { frames: 8, type: 'animated', speed: 'slow' }, // Animation de vent
    bushes: { frames: 8, type: 'animated', speed: 'slow' }, // Animation de vent
    sheep_grass: { frames: 12, type: 'animated', speed: 'normal' },
    sheep_idle: { frames: 6, type: 'animated', speed: 'normal' },
    sheep_move: { frames: 4, type: 'animated', speed: 'normal' },
    gold_highlight: { frames: 6, type: 'animated', speed: 'slow' },
    rubber_duck: { frames: 3, type: 'animated', speed: 'slow' },
    archer_idle: { frames: 6, type: 'animated', speed: 'normal' },
    archer_run: { frames: 4, type: 'animated', speed: 'fast' },
    archer_shoot: { frames: 8, type: 'animated', speed: 'fast' },
    pawn_idle: { frames: 8, type: 'animated', speed: 'normal' },
    pawn_run: { frames: 6, type: 'animated', speed: 'fast' },
    warrior_idle: { frames: 8, type: 'animated', speed: 'normal' },
    warrior_run: { frames: 6, type: 'animated', speed: 'fast' }, 
    warrior_attack: { frames: 4, type: 'animated', speed: 'fast' },
    warrior_guard: { frames: 6, type: 'animated', speed: 'normal' },
    gold_resources: { frames: 1, type: 'static' },
    wood_resources: { frames: 1, type: 'static' },
    meat_resources: { frames: 1, type: 'static' },
    tools: { frames: 1, type: 'static' },
    
    // === ENTITÉS STATIQUES (Variations) ===
    stump: { frames: 1, type: 'static' },
    rocks: { frames: 1, type: 'static' },
    clouds: { frames: 1, type: 'static' },
    rocks_in_water: { frames: 16, type: 'static' }, // 16 variations
    buildings: { frames: 1, type: 'static' },
    human_avatar: { frames: 1, type: 'static' },
    cursor: { frames: 1, type: 'static' },
    archer_arrow: { frames: 1, type: 'static' } 
};