# settings.py — All tunable constants for "Just One More Try"

# ── DEBUG pygame import (safe for headless tests) ───────────────────────────
try:
    import pygame
    DEBUG_TROLL_KEY = pygame.K_F1
except ImportError:
    DEBUG_TROLL_KEY = 290

# ── DISPLAY ──────────────────────────────────────────────────────────────────
SCREEN_W   = 1366
SCREEN_H   = 768
FPS        = 60
TILE_SIZE  = 48
TITLE      = "Just One More Try"

# ── COLOURS (RGB tuples) ─────────────────────────────────────────────────────
BLACK   = (0,   0,   0)
WHITE   = (255, 255, 255)
RED     = (220,  50,  50)
GREEN   = ( 50, 200,  50)
BLUE    = ( 50,  50, 220)
YELLOW  = (255, 215,   0)
ORANGE  = (255, 140,   0)
PURPLE  = (150,  50, 200)
CYAN    = ( 50, 220, 220)

BG_COLOUR                  = ( 20,  20,  35)
PLATFORM_COLOUR            = ( 80,  60,  40)
PLAYER_COLOUR              = (220, 100,  60)
HAZARD_COLOUR              = (220,  30,  30)
CHECKPOINT_COLOUR_INACTIVE = (100, 100, 180)
CHECKPOINT_COLOUR_ACTIVE   = (255, 215,   0)
GOAL_COLOUR                = ( 50, 200,  50)
HUD_COLOUR                 = (255, 255, 255)
DEATH_MSG_COLOUR           = (255,  80,  80)
SLIPPERY_COLOUR            = (180, 230, 255)

# ── PHYSICS ───────────────────────────────────────────────────────────────────
GRAVITY        = 1800.0
JUMP_SPEED     = -680.0
MAX_FALL_SPEED = 1200.0
WALK_SPEED     = 320.0
GROUND_FRICTION = 0.75
AIR_FRICTION    = 0.90
FIXED_DT        = 1.0 / 60.0

# Player dimensions (pixels)
# Width remains standard tile width minus inset (44px), height increased to 60px:
PLAYER_WIDTH   = TILE_SIZE - 4
PLAYER_HEIGHT  = 60

# ── TROLL — Base Defaults (Starting points) ──────────────────────────────────
TROLL_JUMP_FACTOR_MIN  = 0.80
TROLL_JUMP_FACTOR_MAX  = 1.20
TROLL_JUMP_MIN_SAFE    = 0.75

TROLL_INPUT_DELAY_MIN_MS  = 50
TROLL_INPUT_DELAY_MAX_MS  = 150
TROLL_INPUT_DELAY_GRACE_S = 2.0
TROLL_INPUT_DELAY_CHANCE  = 0.35

TROLL_CHECKPOINT_FAIL_CHANCE  = 0.20
TROLL_CHECKPOINT_NEVER_TWICE  = True

TROLL_SLIPPERY_FRICTION_MULT = 0.40

TROLL_VANISH_DELAY_S   = 0.30
TROLL_VANISH_RESPAWN_S = 3.0

TROLL_INVISIBLE = True

# ── LEVEL-BY-LEVEL DIFFICULTY SCALING ────────────────────────────────────────
# Hardness increases progressively for each level (1-indexed):
# Level 1: Gentle introduction (mild jump variance)
# Level 2: Noticeable input latency spikes on jumps
# Level 3: Checkpoints frequently fail, higher input delay chance
# Level 4: Extremely slippery platform edges, tighter jumps
# Level 5: Maximum troll hardness: fast vanishing platforms, high fail rate
LEVEL_DIFFICULTY = {
    1: {
        'jump_min': 0.88, 'jump_max': 1.12,
        'delay_min_ms': 40, 'delay_max_ms': 90, 'delay_chance': 0.20, 'delay_grace': 3.0,
        'checkpoint_fail_chance': 0.10,
        'slippery_mult': 0.60,
        'vanish_delay_s': 0.50,
    },
    2: {
        'jump_min': 0.84, 'jump_max': 1.16,
        'delay_min_ms': 60, 'delay_max_ms': 130, 'delay_chance': 0.35, 'delay_grace': 2.0,
        'checkpoint_fail_chance': 0.20,
        'slippery_mult': 0.50,
        'vanish_delay_s': 0.40,
    },
    3: {
        'jump_min': 0.80, 'jump_max': 1.20,
        'delay_min_ms': 80, 'delay_max_ms': 160, 'delay_chance': 0.45, 'delay_grace': 1.5,
        'checkpoint_fail_chance': 0.35,
        'slippery_mult': 0.38,
        'vanish_delay_s': 0.32,
    },
    4: {
        'jump_min': 0.77, 'jump_max': 1.23,
        'delay_min_ms': 100, 'delay_max_ms': 180, 'delay_chance': 0.55, 'delay_grace': 1.0,
        'checkpoint_fail_chance': 0.45,
        'slippery_mult': 0.25,
        'vanish_delay_s': 0.25,
    },
    5: {
        'jump_min': 0.75, 'jump_max': 1.25,
        'delay_min_ms': 120, 'delay_max_ms': 220, 'delay_chance': 0.65, 'delay_grace': 0.5,
        'checkpoint_fail_chance': 0.55,
        'slippery_mult': 0.15,
        'vanish_delay_s': 0.18,
    },
}

# ── TROLL SEED ────────────────────────────────────────────────────────────────
TROLL_RANDOM_SEED = 42

# ── DEBUG ─────────────────────────────────────────────────────────────────────
DEBUG               = False
DEBUG_SHOW_HITBOXES = False
# DEBUG_TROLL_KEY set near the top of this file

# ── DEATH MESSAGES ────────────────────────────────────────────────────────────
DEATH_MESSAGES = [
    "So close… not.",
    "Gravity says no.",
    "Skill issue.",
    "Try again (lol).",
    "You died. Shocker.",
    "Have you tried not dying?",
    "This is fine.",
    "One more try! (you said that last time)",
    "Classic.",
    "Maybe next time?",
    "Darwin Award candidate.",
    "Oops. Anyway.",
    "The floor is lava. Literally.",
    "Physics: 1, You: 0",
    "Even the goal is judging you.",
    "Bold strategy. Didn't pay off.",
    "That was… something.",
    "You almost had it. Almost.",
    "The void enjoyed that.",
    "Respawning your dignity… failed.",
]
