"""
game.py — Game Manager for "Just One More Try"

Ties together all subsystems: level loading, physics/player, troll engine,
and UI.  Owns the main fixed-timestep loop, the state machine, and all
rendering.

States
------
'menu'           → title screen, waiting for SPACE
'playing'        → normal gameplay
'dead'           → death screen (1.5 s lock before input accepted)
'level_complete' → level-cleared screen (1.0 s lock)
'win'            → all levels beaten
"""

import sys
import os

import pygame

from settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    BG_COLOUR, DEBUG, DEBUG_TROLL_KEY, DEBUG_SHOW_HITBOXES,
    FIXED_DT, TILE_SIZE,
    PLATFORM_COLOUR, HAZARD_COLOUR,
    CHECKPOINT_COLOUR_ACTIVE, CHECKPOINT_COLOUR_INACTIVE,
    GOAL_COLOUR, PLAYER_COLOUR, SLIPPERY_COLOUR,
    WHITE, BLACK, LEVEL_DIFFICULTY,
)
from player import Player
from level import LevelManager
from troll import TrollEngine
from ui import UIManager
import physics


class Game:
    """Central controller: state machine + fixed-timestep loop."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.screen: pygame.Surface = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H)
        )
        self.clock: pygame.time.Clock = pygame.time.Clock()

        # --- state machine ---
        self.state: str = 'menu'

        # --- subsystems ---
        base_dir = os.path.dirname(__file__)
        level_paths = [
            os.path.join(base_dir, 'levels', f'level{i}.txt')
            for i in range(1, 6)
        ]
        self.level_manager: LevelManager = LevelManager(level_paths)
        self.troll_engine: TrollEngine = TrollEngine()
        self.ui: UIManager = UIManager()

        # --- scoring / attempt counters ---
        self.score: int = 0
        self.attempts: int = 0        # total across all levels
        self.level_attempts: int = 0  # for the current level only

        # --- runtime objects (set in _start_level) ---
        self.player: Player | None = None
        self.level = None  # LevelData returned by LevelManager.load()

        # --- timers ---
        self._dead_timer: float = 0.0      # lock input for 1.5 s after death
        self._complete_timer: float = 0.0  # lock input for 1.0 s after clear

        # --- checkpoint flash ---
        self._checkpoint_flash: bool = False
        self._checkpoint_flash_timer: float = 0.0
        self._CHECKPOINT_FLASH_DURATION: float = 0.8  # seconds

        # --- tracks highest checkpoint the player has saved ---
        self._last_checkpoint_idx: int = -1

    # ------------------------------------------------------------------
    # Level loading
    # ------------------------------------------------------------------

    def _start_level(self, index: int) -> None:
        """Load level *index*, wire everything up, enter 'playing'."""
        # 1. Load level data
        self.level = self.level_manager.load(index)

        # 2 & 3. Tell troll engine which trolls are active and hand it the level
        self.troll_engine.set_active(self.level.active_trolls)
        self.troll_engine.apply_difficulty(index + 1)
        self.troll_engine.set_level(self.level)

        # 4. Collect behaviour hooks the troll engine exposes to the player
        hooks = self.troll_engine.get_hooks()

        # 5. Spawn the player at the level's spawn point
        self.player = Player(self.level.spawn, hooks)
        diff = LEVEL_DIFFICULTY.get(index + 1, {})
        if 'slippery_mult' in diff:
            self.player.slippery_friction_mult = diff['slippery_mult']

        # 6. Reset both subsystems so troll timers / vanishing tiles start fresh
        self.troll_engine.reset()
        self.level.reset()
        if hasattr(self.level, 'set_difficulty'):
            self.level.set_difficulty(index + 1)

        # 7. Per-level attempt counter
        self.level_attempts = 0

        # 8. Reset checkpoint tracking
        self._last_checkpoint_idx = -1

        self.state = 'playing'

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Fixed-timestep game loop (60 Hz physics, uncapped render)."""
        accumulator: float = 0.0
        prev_time: float = pygame.time.get_ticks() / 1000.0

        while True:
            now: float = pygame.time.get_ticks() / 1000.0
            frame_dt: float = min(now - prev_time, 0.05)  # cap at 50 ms
            prev_time = now
            accumulator += frame_dt

            self._handle_events()

            # Consume fixed steps
            while accumulator >= FIXED_DT:
                self._update(FIXED_DT)
                accumulator -= FIXED_DT

            self._draw()
            self.clock.tick(FPS)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        """Process the pygame event queue."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.KEYDOWN:
                self._on_keydown(event.key)

    def _on_keydown(self, key: int) -> None:
        """Dispatch a single KEYDOWN key."""
        # --- always-available keys ---
        if key == pygame.K_ESCAPE:
            # Return to menu from anywhere; quit from menu
            if self.state == 'menu':
                sys.exit()
            else:
                self.state = 'menu'
            return

        # --- debug: toggle troll engine ---
        if DEBUG and key == DEBUG_TROLL_KEY:
            for troll_name in self.level.active_trolls:
                self.troll_engine.toggle(troll_name)
            return

        # --- restart current level ---
        if key == pygame.K_r and self.state in ('dead', 'playing'):
            self._start_level(self.level_manager.current_index)
            return

        # --- SPACE: context-sensitive confirm / advance ---
        if key == pygame.K_SPACE:
            if self.state == 'menu':
                # Start a fresh run
                self.attempts = 0
                self.score = 0
                self._start_level(0)

            elif self.state == 'dead' and self._dead_timer > 1.5:
                # Respawn without resetting level index
                self.player.respawn()
                self.level.reset()
                self.troll_engine.reset()
                self._last_checkpoint_idx = -1
                self.state = 'playing'

            elif self.state == 'level_complete' and self._complete_timer > 1.0:
                # Advance to the next level (or win screen)
                next_level = self.level_manager.next_level()
                if next_level is not None:
                    self._start_level(self.level_manager.current_index)
                else:
                    self.state = 'win'

            elif self.state == 'win':
                self.state = 'menu'

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        """Fixed-timestep update.  Only simulates when state == 'playing'."""
        # Advance overlay timers even when not playing
        if self.state == 'dead':
            self._dead_timer += dt
            return
        if self.state == 'level_complete':
            self._complete_timer += dt
            return
        if self.state != 'playing':
            return

        # --- input + physics ---
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, dt)

        result = self.player.update(
            dt,
            self.level.get_solid_rects(),
            self.level.hazards,
            self.level.checkpoints,
            self.level.goal,
            self.level.slippery_tiles,
            self.level,
        )

        # --- vanishing platforms (driven from here, not from troll.on_update) ---
        self.level.update_vanishing(
            dt,
            'vanishing_platforms' in self.level.active_trolls,
        )

        # --- troll engine per-frame hook ---
        self.troll_engine.on_update(dt)

        # --- handle player result ---
        if result == 'dead':
            self.attempts += 1
            self.level_attempts += 1
            self.state = 'dead'
            self._dead_timer = 0.0
            self.ui.new_death_message()

        elif result == 'checkpoint':
            # Update the highest saved checkpoint index
            checkpoint_idx = self.player.last_checkpoint_idx
            if checkpoint_idx > self._last_checkpoint_idx:
                self._last_checkpoint_idx = checkpoint_idx
            self.score += 10
            self._checkpoint_flash = True
            self._checkpoint_flash_timer = 0.0

        elif result == 'goal':
            self.score += 100
            self.state = 'level_complete'
            self._complete_timer = 0.0

        # --- checkpoint flash timer ---
        if self._checkpoint_flash:
            self._checkpoint_flash_timer += dt
            if self._checkpoint_flash_timer >= self._CHECKPOINT_FLASH_DURATION:
                self._checkpoint_flash = False
                self._checkpoint_flash_timer = 0.0

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        """Render one frame."""
        surface = self.screen
        surface.fill(BG_COLOUR)

        # --- menu is self-contained ---
        if self.state == 'menu':
            self.ui.draw_menu(surface)
            pygame.display.flip()
            return

        # === draw level ===
        self._draw_level(surface)

        # === draw player ===
        if self.player is not None:
            self._draw_player(surface)

        # === troll engine overlays (e.g. debug outlines) ===
        self.troll_engine.draw(surface)

        # === HUD ===
        self.ui.draw_hud(
            surface,
            level_num=self.level_manager.current_index + 1,
            attempts=self.attempts,
            score=self.score,
            checkpoint_flash=self._checkpoint_flash,
        )

        # === overlay screens ===
        if self.state == 'dead':
            self.ui.draw_death(surface, self.level_attempts)

        elif self.state == 'level_complete':
            self.ui.draw_level_complete(
                surface,
                self.level_manager.current_index + 1,
                self.level_attempts,
            )

        elif self.state == 'win':
            self.ui.draw_win(surface, self.attempts, self.score)

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _draw_level(self, surface: pygame.Surface) -> None:
        """Draw all level geometry."""
        level = self.level

        # --- solid platform tiles ---
        for rect in level.platforms:
            pygame.draw.rect(surface, PLATFORM_COLOUR, rect)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, rect, 1)

        # --- slippery tiles (drawn on top of platform colour) ---
        for rect in level.slippery_tiles:
            pygame.draw.rect(surface, SLIPPERY_COLOUR, rect)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, rect, 1)

        # --- vanishing platform tiles ---
        for vp in level.vanishing_platforms:
            vstate = vp.state  # 'solid', 'vanishing', 'gone'
            if vstate == 'gone':
                continue
            if vstate == 'solid':
                colour = PLATFORM_COLOUR
            else:
                # 'vanishing': fade from PLATFORM_COLOUR toward BG_COLOUR
                t = max(0.0, min(1.0, vp.timer / vp.vanish_delay))
                colour = self._lerp_colour(PLATFORM_COLOUR, BG_COLOUR, t)
            pygame.draw.rect(surface, colour, vp.rect)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, vp.rect, 1)

        # --- invisible tiles ---
        for rect in level.invisible_platforms:
            if DEBUG:
                # Draw a faint outline so the developer can see them
                faint = (60, 60, 80)
                pygame.draw.rect(surface, faint, rect, 1)
            # In release mode: draw nothing

        # --- hazards ---
        for rect in level.hazards:
            pygame.draw.rect(surface, HAZARD_COLOUR, rect)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, rect, 1)

        # --- checkpoints ---
        for idx, cp in enumerate(level.checkpoints):
            colour = (
                CHECKPOINT_COLOUR_ACTIVE
                if idx <= self._last_checkpoint_idx
                else CHECKPOINT_COLOUR_INACTIVE
            )
            pygame.draw.rect(surface, colour, cp.rect)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, cp.rect, 1)

        # --- goal ---
        if level.goal is not None:
            pygame.draw.rect(surface, GOAL_COLOUR, level.goal)
            if DEBUG and DEBUG_SHOW_HITBOXES:
                pygame.draw.rect(surface, WHITE, level.goal, 1)

    def _draw_player(self, surface: pygame.Surface) -> None:
        """Draw Shinchan character sprite for the player."""
        p = self.player
        rect = p.rect
        rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
        facing = getattr(p, 'facing', 1)

        # Palette
        SKIN = (255, 218, 185)       # warm peach skin
        CHEEK = (255, 140, 160)      # rosy blush
        HAIR = (20, 20, 20)          # black hair / thick brows
        SHIRT = (235, 45, 35)        # iconic red t-shirt
        SHORTS = (255, 225, 30)      # bright yellow shorts
        SHOES = (255, 255, 255)      # white socks/shoes
        OUTLINE = (30, 20, 20)       # crisp cartoon outline
        EYE_WHITE = (255, 255, 255)

        # 1. Shoes / Feet (Bottom)
        foot_y = ry + int(rh * 0.90)
        foot_h = rh - int(rh * 0.90)
        foot_w = int(rw * 0.32)
        # Left and Right shoes
        pygame.draw.ellipse(surface, SHOES, (rx + int(rw * 0.12), foot_y, foot_w, foot_h))
        pygame.draw.ellipse(surface, OUTLINE, (rx + int(rw * 0.12), foot_y, foot_w, foot_h), 1)
        pygame.draw.ellipse(surface, SHOES, (rx + int(rw * 0.56), foot_y, foot_w, foot_h))
        pygame.draw.ellipse(surface, OUTLINE, (rx + int(rw * 0.56), foot_y, foot_w, foot_h), 1)

        # 2. Yellow Shorts
        pants_y = ry + int(rh * 0.68)
        pants_h = int(rh * 0.24)
        pants_w = int(rw * 0.76)
        pants_x = rx + int(rw * 0.12)
        pygame.draw.rect(surface, SHORTS, (pants_x, pants_y, pants_w, pants_h), border_radius=3)
        pygame.draw.rect(surface, OUTLINE, (pants_x, pants_y, pants_w, pants_h), 1, border_radius=3)

        # 3. Red Shirt / Torso
        shirt_y = ry + int(rh * 0.44)
        shirt_h = int(rh * 0.28)
        shirt_w = int(rw * 0.82)
        shirt_x = rx + int(rw * 0.09)
        pygame.draw.rect(surface, SHIRT, (shirt_x, shirt_y, shirt_w, shirt_h), border_radius=4)
        pygame.draw.rect(surface, OUTLINE, (shirt_x, shirt_y, shirt_w, shirt_h), 1, border_radius=4)

        # 4. Shinchan's iconic chubby head (wider on the cheek side)
        head_y = ry + 2
        head_h = int(rh * 0.48)
        head_w = int(rw * 0.88)
        head_x = rx + int(rw * 0.06)

        # Black hair base (slightly behind head)
        hair_rect = pygame.Rect(head_x, head_y, head_w, int(head_h * 0.60))
        pygame.draw.ellipse(surface, HAIR, hair_rect)

        # Chubby head ellipse
        face_rect = pygame.Rect(head_x, head_y + 3, head_w, head_h)
        pygame.draw.ellipse(surface, SKIN, face_rect)
        pygame.draw.ellipse(surface, OUTLINE, face_rect, 1)

        # Shinchan spiky/cropped hair silhouette on top
        if facing == 1:
            pygame.draw.polygon(surface, HAIR, [
                (head_x + 2, head_y + 10),
                (head_x + int(head_w * 0.20), head_y),
                (head_x + int(head_w * 0.55), head_y),
                (head_x + int(head_w * 0.70), head_y + 8),
                (head_x + 5, head_y + 14)
            ])
        else:
            pygame.draw.polygon(surface, HAIR, [
                (head_x + head_w - 2, head_y + 10),
                (head_x + head_w - int(head_w * 0.20), head_y),
                (head_x + head_w - int(head_w * 0.55), head_y),
                (head_x + head_w - int(head_w * 0.70), head_y + 8),
                (head_x + head_w - 5, head_y + 14)
            ])

        # 5. Thick Signature Wavy Eyebrows
        brow_y = head_y + int(head_h * 0.30)
        brow_w = max(4, int(head_w * 0.26))
        brow_h = max(2, int(head_h * 0.16))

        if facing == 1:
            # facing right
            b1_x = head_x + int(head_w * 0.25)
            b2_x = head_x + int(head_w * 0.58)
        else:
            # facing left
            b1_x = head_x + int(head_w * 0.16)
            b2_x = head_x + int(head_w * 0.49)

        pygame.draw.ellipse(surface, HAIR, (b1_x, brow_y, brow_w, brow_h))
        pygame.draw.ellipse(surface, HAIR, (b2_x, brow_y, brow_w, brow_h))

        # 6. Big Cartoony Eyes
        eye_y = brow_y + brow_h + 1
        eye_r = max(2, int(head_w * 0.10))
        pupil_r = max(1, eye_r - 2)

        if facing == 1:
            e1_x = b1_x + brow_w // 2
            e2_x = b2_x + brow_w // 2
            pupil_offset = 1
        else:
            e1_x = b1_x + brow_w // 2
            e2_x = b2_x + brow_w // 2
            pupil_offset = -1

        # Left eye
        pygame.draw.circle(surface, EYE_WHITE, (e1_x, eye_y + eye_r), eye_r)
        pygame.draw.circle(surface, OUTLINE, (e1_x, eye_y + eye_r), eye_r, 1)
        pygame.draw.circle(surface, HAIR, (e1_x + pupil_offset, eye_y + eye_r), pupil_r)

        # Right eye
        pygame.draw.circle(surface, EYE_WHITE, (e2_x, eye_y + eye_r), eye_r)
        pygame.draw.circle(surface, OUTLINE, (e2_x, eye_y + eye_r), eye_r, 1)
        pygame.draw.circle(surface, HAIR, (e2_x + pupil_offset, eye_y + eye_r), pupil_r)

        # 7. Rosy Chubby Cheek
        cheek_r = max(2, int(head_w * 0.11))
        if facing == 1:
            cheek_x = head_x + int(head_w * 0.74)
        else:
            cheek_x = head_x + int(head_w * 0.26)
        cheek_y = eye_y + eye_r + 2
        pygame.draw.circle(surface, CHEEK, (cheek_x, cheek_y), cheek_r)

        # 8. Mischievous smile / mouth
        mouth_y = cheek_y + 1
        mouth_w = max(3, int(head_w * 0.18))
        if facing == 1:
            mouth_x = head_x + int(head_w * 0.50)
            pygame.draw.arc(surface, OUTLINE, (mouth_x, mouth_y - 2, mouth_w, 6), 3.14, 6.28, 2)
        else:
            mouth_x = head_x + int(head_w * 0.32)
            pygame.draw.arc(surface, OUTLINE, (mouth_x, mouth_y - 2, mouth_w, 6), 3.14, 6.28, 2)

        if DEBUG and DEBUG_SHOW_HITBOXES:
            pygame.draw.rect(surface, WHITE, rect, 1)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _lerp_colour(
        c1: tuple[int, int, int],
        c2: tuple[int, int, int],
        t: float,
    ) -> tuple[int, int, int]:
        """Linear interpolate between two RGB colours.  t=0 → c1, t=1 → c2."""
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )
