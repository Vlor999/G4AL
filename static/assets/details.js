const SPRITE_CONFIG = {
    // ═══════════════════════════════════════════════════════════════════
    //  ENTITÉS ANIMÉES (sprite sheets avec saut de frame)
    // ═══════════════════════════════════════════════════════════════════

    // --- Terrain / Nature ---
    trees: {
        frames: 8, type: 'animated', speed: 'slow',
        files_or_dir: [
            "static/assets/Terrain/Resources/Wood/Trees/Tree1.png",
            "static/assets/Terrain/Resources/Wood/Trees/Tree2.png",
            "static/assets/Terrain/Resources/Wood/Trees/Tree3.png",
            "static/assets/Terrain/Resources/Wood/Trees/Tree4.png",
        ]
    },
    bushes: {
        frames: 8, type: 'animated', speed: 'slow',
        files_or_dir: [
            "static/assets/Terrain/Decorations/Bushes/Bushe1.png",
            "static/assets/Terrain/Decorations/Bushes/Bushe2.png",
            "static/assets/Terrain/Decorations/Bushes/Bushe3.png",
            "static/assets/Terrain/Decorations/Bushes/Bushe4.png",
        ]
    },
    rubber_duck: {
        frames: 3, type: 'animated', speed: 'slow',
        files_or_dir: "static/assets/Terrain/Decorations/Rubber Duck/Rubber duck.png"
    },

    // --- Animaux ---
    sheep_grass: {
        frames: 12, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Terrain/Resources/Meat/Sheep/Sheep_Grass.png"
    },
    sheep_idle: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Terrain/Resources/Meat/Sheep/Sheep_Idle.png"
    },
    sheep_move: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Terrain/Resources/Meat/Sheep/Sheep_Move.png"
    },

    // --- Ressources animées ---
    gold_highlight: {
        frames: 6, type: 'animated', speed: 'slow',
        files_or_dir: [
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 1_Highlight.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 2_Highlight.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 3_Highlight.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 4_Highlight.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 5_Highlight.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 6_Highlight.png",
        ]
    },
    gold_resource_highlight: {
        frames: 6, type: 'animated', speed: 'slow',
        files_or_dir: "static/assets/Terrain/Resources/Gold/Gold Resource/Gold_Resource_Highlight.png"
    },

    // --- Water ---
    water_foam: {
        frames: 16, type: 'animated', speed: 'slow',
        files_or_dir: "static/assets/Terrain/Tileset/Water Foam.png"
    },

    // --- Unités : Pawn ---
    pawn_idle: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle.png"
    },
    pawn_run: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run.png"
    },
    pawn_idle_axe: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Axe.png"
    },
    pawn_idle_pickaxe: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Pickaxe.png"
    },
    pawn_idle_hammer: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Hammer.png"
    },
    pawn_idle_knife: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Knife.png"
    },
    pawn_idle_wood: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Wood.png"
    },
    pawn_idle_gold: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Gold.png"
    },
    pawn_idle_meat: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Idle Meat.png"
    },
    pawn_run_axe: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Axe.png"
    },
    pawn_run_pickaxe: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Pickaxe.png"
    },
    pawn_run_hammer: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Hammer.png"
    },
    pawn_run_wood: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Wood.png"
    },
    pawn_run_gold: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Gold.png"
    },
    pawn_run_meat: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Run Meat.png"
    },
    pawn_interact_axe: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Interact Axe.png"
    },
    pawn_interact_pickaxe: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Interact Pickaxe.png"
    },
    pawn_interact_hammer: {
        frames: 3, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Interact Hammer.png"
    },
    pawn_interact_knife: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Pawn/Pawn_Interact Knife.png"
    },

    // --- Unités : Archer ---
    archer_idle: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Archer/Archer_Idle.png"
    },
    archer_run: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Archer/Archer_Run.png"
    },
    archer_shoot: {
        frames: 8, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Archer/Archer_Shoot.png"
    },

    // --- Unités : Warrior ---
    warrior_idle: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Warrior/Warrior_Idle.png"
    },
    warrior_run: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Warrior/Warrior_Run.png"
    },
    warrior_attack1: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Warrior/Warrior_Attack1.png"
    },
    warrior_attack2: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Warrior/Warrior_Attack2.png"
    },
    warrior_guard: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Warrior/Warrior_Guard.png"
    },

    // --- Unités : Lancer ---
    lancer_idle: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Idle.png"
    },
    lancer_run: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Run.png"
    },
    lancer_down_attack: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Down_Attack.png"
    },
    lancer_down_defence: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Down_Defence.png"
    },
    lancer_right_attack: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Right_Attack.png"
    },
    lancer_right_defence: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Right_Defence.png"
    },
    lancer_up_attack: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Up_Attack.png"
    },
    lancer_up_defence: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_Up_Defence.png"
    },
    lancer_downright_attack: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_DownRight_Attack.png"
    },
    lancer_downright_defence: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_DownRight_Defence.png"
    },
    lancer_upright_attack: {
        frames: 4, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_UpRight_Attack.png"
    },
    lancer_upright_defence: {
        frames: 4, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Lancer/Lancer_UpRight_Defence.png"
    },

    // --- Unités : Monk ---
    monk_idle: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Monk/Idle.png"
    },
    monk_run: {
        frames: 6, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Units/Blue Units/Monk/Run.png"
    },
    monk_heal: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Monk/Heal.png"
    },
    monk_heal_effect: {
        frames: 6, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Units/Blue Units/Monk/Heal_Effect.png"
    },

    // --- Particules d'effets ---
    dust_1: {
        frames: 8, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Particle FX/Dust_01.png"
    },
    dust_2: {
        frames: 10, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Particle FX/Dust_02.png"
    },
    explosion_1: {
        frames: 8, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Particle FX/Explosion_01.png"
    },
    explosion_2: {
        frames: 10, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Particle FX/Explosion_02.png"
    },
    fire_1: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Particle FX/Fire_01.png"
    },
    fire_2: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Particle FX/Fire_02.png"
    },
    fire_3: {
        frames: 8, type: 'animated', speed: 'normal',
        files_or_dir: "static/assets/Particle FX/Fire_03.png"
    },
    water_splash: {
        frames: 9, type: 'animated', speed: 'fast',
        files_or_dir: "static/assets/Particle FX/Water Splash.png"
    },

    // ═══════════════════════════════════════════════════════════════════
    //  ENTITÉS STATIQUES (1 sprite par image, ou variations)
    // ═══════════════════════════════════════════════════════════════════

    // --- Terrain / Ressources ---
    stump: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Resources/Wood/Trees/Stump 1.png",
            "static/assets/Terrain/Resources/Wood/Trees/Stump 2.png",
            "static/assets/Terrain/Resources/Wood/Trees/Stump 3.png",
            "static/assets/Terrain/Resources/Wood/Trees/Stump 4.png",
        ]
    },
    rocks: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Decorations/Rocks/Rock1.png",
            "static/assets/Terrain/Decorations/Rocks/Rock2.png",
            "static/assets/Terrain/Decorations/Rocks/Rock3.png",
            "static/assets/Terrain/Decorations/Rocks/Rock4.png",
        ]
    },
    rocks_in_water: {
        frames: 16, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Decorations/Rocks in the Water/Water Rocks_01.png",
            "static/assets/Terrain/Decorations/Rocks in the Water/Water Rocks_02.png",
            "static/assets/Terrain/Decorations/Rocks in the Water/Water Rocks_03.png",
            "static/assets/Terrain/Decorations/Rocks in the Water/Water Rocks_04.png",
        ]
    },
    gold_stones: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 1.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 2.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 3.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 4.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 5.png",
            "static/assets/Terrain/Resources/Gold/Gold Stones/Gold Stone 6.png",
        ]
    },
    gold_resource: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Resources/Gold/Gold Resource/Gold_Resource.png"
    },
    wood_resource: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Resources/Wood/Wood Resource/Wood Resource.png"
    },
    meat_resource: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Resources/Meat/Meat Resource/Meat Resource.png"
    },
    tools: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Resources/Tools/Tool_01.png",
            "static/assets/Terrain/Resources/Tools/Tool_02.png",
            "static/assets/Terrain/Resources/Tools/Tool_03.png",
            "static/assets/Terrain/Resources/Tools/Tool_04.png",
        ]
    },
    clouds: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/Terrain/Decorations/Clouds/Clouds_01.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_02.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_03.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_04.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_05.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_06.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_07.png",
            "static/assets/Terrain/Decorations/Clouds/Clouds_08.png",
        ]
    },

    // --- Bâtiments (Blue) ---
    // gridWidth / gridHeight = ground-footprint in tiles
    buildings: {
        frames: 1, type: 'static',
        files_or_dir: {
            archery:    "static/assets/Buildings/Blue Buildings/Archery.png",
            barracks:   "static/assets/Buildings/Blue Buildings/Barracks.png",
            castle:     "static/assets/Buildings/Blue Buildings/Castle.png",
            house1:     "static/assets/Buildings/Blue Buildings/House1.png",
            house2:     "static/assets/Buildings/Blue Buildings/House2.png",
            house3:     "static/assets/Buildings/Blue Buildings/House3.png",
            monastery:  "static/assets/Buildings/Blue Buildings/Monastery.png",
            tower:      "static/assets/Buildings/Blue Buildings/Tower.png",
        },
        grid: {
            archery:   { w: 3, h: 3 },
            barracks:  { w: 3, h: 3 },
            castle:    { w: 5, h: 3 },
            house1:    { w: 2, h: 2 },
            house2:    { w: 2, h: 2 },
            house3:    { w: 2, h: 2 },
            monastery: { w: 3, h: 3 },
            tower:     { w: 2, h: 2 },
        }
    },

    // --- Unités : Arrow (projectile statique) ---
    archer_arrow: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Units/Blue Units/Archer/Arrow.png"
    },

    // --- Tilesets ---
    tileset_color1: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Tilemap_color1.png"
    },
    tileset_color2: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Tilemap_color2.png"
    },
    tileset_color3: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Tilemap_color3.png"
    },
    tileset_color4: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Tilemap_color4.png"
    },
    tileset_color5: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Tilemap_color5.png"
    },
    water_bg: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Water Background color.png"
    },
    shadow: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/Terrain/Tileset/Shadow.png"
    },

    // --- UI Elements ---
    ui_banners: {
        frames: 1, type: 'static',
        files_or_dir: {
            banner:       "static/assets/UI Elements/UI Elements/Banners/Banner.png",
            banner_slots: "static/assets/UI Elements/UI Elements/Banners/Banner_Slots.png",
        }
    },
    ui_bars: {
        frames: 1, type: 'static',
        files_or_dir: {
            big_base:   "static/assets/UI Elements/UI Elements/Bars/BigBar_Base.png",
            big_fill:   "static/assets/UI Elements/UI Elements/Bars/BigBar_Fill.png",
            small_base: "static/assets/UI Elements/UI Elements/Bars/SmallBar_Base.png",
            small_fill: "static/assets/UI Elements/UI Elements/Bars/SmallBar_Fill.png",
        }
    },
    ui_buttons: {
        frames: 1, type: 'static',
        files_or_dir: {
            big_blue_pressed:        "static/assets/UI Elements/UI Elements/Buttons/BigBlueButton_Pressed.png",
            big_blue_regular:        "static/assets/UI Elements/UI Elements/Buttons/BigBlueButton_Regular.png",
            big_red_pressed:         "static/assets/UI Elements/UI Elements/Buttons/BigRedButton_Pressed.png",
            big_red_regular:         "static/assets/UI Elements/UI Elements/Buttons/BigRedButton_Regular.png",
            small_blue_round_pressed:"static/assets/UI Elements/UI Elements/Buttons/SmallBlueRoundButton_Pressed.png",
            small_blue_round_regular:"static/assets/UI Elements/UI Elements/Buttons/SmallBlueRoundButton_Regular.png",
            small_blue_sq_pressed:   "static/assets/UI Elements/UI Elements/Buttons/SmallBlueSquareButton_Pressed.png",
            small_blue_sq_regular:   "static/assets/UI Elements/UI Elements/Buttons/SmallBlueSquareButton_Regular.png",
            small_red_round_pressed: "static/assets/UI Elements/UI Elements/Buttons/SmallRedRoundButton_Pressed.png",
            small_red_round_regular: "static/assets/UI Elements/UI Elements/Buttons/SmallRedRoundButton_Regular.png",
            small_red_sq_pressed:    "static/assets/UI Elements/UI Elements/Buttons/SmallRedSquareButton_Pressed.png",
            small_red_sq_regular:    "static/assets/UI Elements/UI Elements/Buttons/SmallRedSquareButton_Regular.png",
            tiny_round_blue:         "static/assets/UI Elements/UI Elements/Buttons/TinyRoundBlueButton.png",
            tiny_round_red:          "static/assets/UI Elements/UI Elements/Buttons/TinyRoundRedButton.png",
            tiny_sq_blue:            "static/assets/UI Elements/UI Elements/Buttons/TinySquareBlueButton.png",
            tiny_sq_red:             "static/assets/UI Elements/UI Elements/Buttons/TinySquareRedButton.png",
        }
    },
    ui_cursors: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/UI Elements/UI Elements/Cursors/Cursor_01.png",
            "static/assets/UI Elements/UI Elements/Cursors/Cursor_02.png",
            "static/assets/UI Elements/UI Elements/Cursors/Cursor_03.png",
            "static/assets/UI Elements/UI Elements/Cursors/Cursor_04.png",
        ]
    },
    human_avatar: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_01.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_02.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_03.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_04.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_05.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_06.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_07.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_08.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_09.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_10.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_11.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_12.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_13.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_14.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_15.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_16.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_17.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_18.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_19.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_20.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_21.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_22.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_23.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_24.png",
            "static/assets/UI Elements/UI Elements/Human Avatars/Avatars_25.png",
        ]
    },
    ui_icons: {
        frames: 1, type: 'static',
        files_or_dir: [
            "static/assets/UI Elements/UI Elements/Icons/Icon_01.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_02.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_03.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_04.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_05.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_06.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_07.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_08.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_09.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_10.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_11.png",
            "static/assets/UI Elements/UI Elements/Icons/Icon_12.png",
        ]
    },
    ui_papers: {
        frames: 1, type: 'static',
        files_or_dir: {
            regular: "static/assets/UI Elements/UI Elements/Papers/RegularPaper.png",
            special: "static/assets/UI Elements/UI Elements/Papers/SpecialPaper.png",
        }
    },
    ui_ribbons: {
        frames: 1, type: 'static',
        files_or_dir: {
            big:   "static/assets/UI Elements/UI Elements/Ribbons/BigRibbons.png",
            small: "static/assets/UI Elements/UI Elements/Ribbons/SmallRibbons.png",
        }
    },
    ui_swords: {
        frames: 1, type: 'static',
        files_or_dir: "static/assets/UI Elements/UI Elements/Swords/Swords.png"
    },
    ui_wood_table: {
        frames: 1, type: 'static',
        files_or_dir: {
            table: "static/assets/UI Elements/UI Elements/Wood Table/WoodTable.png",
            slots: "static/assets/UI Elements/UI Elements/Wood Table/WoodTable_Slots.png",
        }
    },
    ui_store_banner: {
        frames: 1, type: 'static',
        files_or_dir: {
            banner: "static/assets/UI Elements/UI Banners from the store page/Banner/Banner.png",
            slots:  "static/assets/UI Elements/UI Banners from the store page/Banner/Slots.png",
        }
    },
    ui_store_ribbons: {
        frames: 1, type: 'static',
        files_or_dir: {
            black:  "static/assets/UI Elements/UI Banners from the store page/Ribbons/Ribbon_Black.png",
            blue:   "static/assets/UI Elements/UI Banners from the store page/Ribbons/Ribbon_Blue.png",
            purple: "static/assets/UI Elements/UI Banners from the store page/Ribbons/Ribbon_Purple.png",
            red:    "static/assets/UI Elements/UI Banners from the store page/Ribbons/Ribbon_Red.png",
            yellow: "static/assets/UI Elements/UI Banners from the store page/Ribbons/Ribbon_Yellow.png",
        }
    },
};