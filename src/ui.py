"""
ui.py — HUD, death messages, menus, and end screens for "Just One More Try".

All drawing is stateless except for checkpoint flash timing (HUD) and the
current death message stored in UIManager.  Callers own the game state; this
module only renders it.
"""

import pygame
import random

from settings import (
    SCREEN_W, SCREEN_H, HUD_COLOUR, DEATH_MSG_COLOUR, BG_COLOUR,
    GOAL_COLOUR, WHITE, BLACK, RED, YELLOW, ORANGE,
    DEATH_MESSAGES, TITLE,
)

# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

class HUD:
    """Renders the top-left heads-up display: level, attempts, score.

    Also shows a temporary "✓ Checkpoint!" flash that fades over 1.5 s.
    """

    _CHECKPOINT_DURATION = 1.5   # seconds the flash is visible
    _PADDING = 10                 # px from edge

    def __init__(self, font: pygame.font.Font):
        self._font = font
        self._checkpoint_timer = 0.0   # counts DOWN from _CHECKPOINT_DURATION

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trigger_checkpoint_flash(self):
        """Call this whenever a checkpoint is successfully saved."""
        self._checkpoint_timer = self._CHECKPOINT_DURATION

    def update(self, dt: float):
        """Advance the checkpoint flash timer.  dt is in seconds."""
        if self._checkpoint_timer > 0.0:
            self._checkpoint_timer = max(0.0, self._checkpoint_timer - dt)

    def draw(
        self,
        surface: pygame.Surface,
        level_num: int,
        attempts: int,
        score: int,
        checkpoint_saved: bool = False,
        checkpoint_flash: bool = False,
        **kwargs,
    ):
        """Draw the HUD onto *surface*.

        Args:
            surface:          The main render surface.
            level_num:        Current 1-based level index.
            attempts:         Total attempts so far.
            score:            Current score.
            checkpoint_saved: If True, start (or restart) the flash timer.
            checkpoint_flash: If True, keep flash active this frame.
        """
        if checkpoint_saved:
            self.trigger_checkpoint_flash()

        x = self._PADDING
        y = self._PADDING
        line_h = self._font.get_linesize() + 2

        lines = [
            f"Level: {level_num}",
            f"Attempts: {attempts}",
            f"Score: {score}",
        ]

        for text in lines:
            surf = self._font.render(text, True, HUD_COLOUR)
            surface.blit(surf, (x, y))
            y += line_h

        # Checkpoint flash
        if self._checkpoint_timer > 0.0 or checkpoint_flash:
            if self._checkpoint_timer > 0.0:
                # Fade: full opacity for first half, then linear fade-out
                progress = self._checkpoint_timer / self._CHECKPOINT_DURATION
                alpha = 255 if progress > 0.5 else int(255 * (progress / 0.5))
            else:
                alpha = 255

            flash_surf = self._font.render("✓ Checkpoint!", True, YELLOW)
            if alpha < 255:
                flash_surf.set_alpha(alpha)
            surface.blit(flash_surf, (x, y))


# ---------------------------------------------------------------------------
# DeathMessage
# ---------------------------------------------------------------------------

class DeathMessage:
    """Picks a random death message, never repeating the last one."""

    def __init__(self):
        self._last: str | None = None

    def pick(self) -> str:
        """Return a random death message, avoiding the previous pick."""
        choices = [m for m in DEATH_MESSAGES if m != self._last]
        # Fallback: if only one message exists, allow repeat
        if not choices:
            choices = DEATH_MESSAGES
        msg = random.choice(choices)
        self._last = msg
        return msg

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        msg: str,
        alpha: int = 255,
    ):
        """Draw *msg* centred on the screen in DEATH_MSG_COLOUR."""
        text_surf = font.render(msg, True, DEATH_MSG_COLOUR)
        text_surf.set_alpha(alpha)
        rect = text_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
        surface.blit(text_surf, rect)


# ---------------------------------------------------------------------------
# MenuScreen
# ---------------------------------------------------------------------------

class MenuScreen:
    """The main menu / title screen."""

    _TAGLINES = [
        "Warning: may cause controller-throwing.",
        "Certified rage-quit material.",
        "Your suffering is our entertainment.",
        "Difficulty: Yes.",
        "It gets worse. Much worse.",
        "Side effects: mild existential dread.",
    ]

    def draw(self, surface: pygame.Surface, font_big: pygame.font.Font, font_small: pygame.font.Font):
        surface.fill(BLACK)

        cx = SCREEN_W // 2

        # Title
        title_surf = font_big.render(TITLE, True, WHITE)
        title_rect = title_surf.get_rect(centerx=cx, top=80)
        surface.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = font_small.render("A troll platformer", True, ORANGE)
        sub_rect = sub_surf.get_rect(centerx=cx, top=title_rect.bottom + 12)
        surface.blit(sub_surf, sub_rect)

        # Separator gap
        y = sub_rect.bottom + 60

        # Controls
        controls_lines = [
            "Arrow keys / WASD to move",
            "Space / W / Up to jump",
        ]
        for line in controls_lines:
            surf = font_small.render(line, True, WHITE)
            rect = surf.get_rect(centerx=cx, top=y)
            surface.blit(surf, rect)
            y += rect.height + 8

        y += 20

        # Start prompt (pulsing via blink — always visible here, caller may animate)
        start_surf = font_small.render("Press SPACE to start", True, WHITE)
        start_rect = start_surf.get_rect(centerx=cx, top=y)
        surface.blit(start_surf, start_rect)

        # Funny tagline at the bottom
        tagline = self._TAGLINES[pygame.time.get_ticks() // 5000 % len(self._TAGLINES)]
        tag_surf = font_small.render(tagline, True, ORANGE)
        tag_rect = tag_surf.get_rect(centerx=cx, bottom=SCREEN_H - 20)
        surface.blit(tag_surf, tag_rect)


# ---------------------------------------------------------------------------
# DeathScreen
# ---------------------------------------------------------------------------

class DeathScreen:
    """Semi-transparent overlay shown when the player dies."""

    _OVERLAY_ALPHA = 160   # 0-255

    def draw(
        self,
        surface: pygame.Surface,
        font_big: pygame.font.Font,
        font_small: pygame.font.Font,
        attempts: int,
        msg: str,
        font_med: pygame.font.Font | None = None,
    ):
        # Dark semi-transparent overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self._OVERLAY_ALPHA))
        surface.blit(overlay, (0, 0))

        cx = SCREEN_W // 2
        y = SCREEN_H // 4

        # "YOU DIED"
        died_surf = font_big.render("YOU DIED", True, RED)
        died_rect = died_surf.get_rect(centerx=cx, top=y)
        surface.blit(died_surf, died_rect)
        y = died_rect.bottom + 24

        # Death message (medium font if provided, else font_small)
        msg_font = font_med or font_small
        msg_surf = msg_font.render(msg, True, DEATH_MSG_COLOUR)
        msg_rect = msg_surf.get_rect(centerx=cx, top=y)
        surface.blit(msg_surf, msg_rect)
        y = msg_rect.bottom + 20

        # Attempts
        att_surf = font_small.render(f"Attempts: {attempts}", True, WHITE)
        att_rect = att_surf.get_rect(centerx=cx, top=y)
        surface.blit(att_surf, att_rect)
        y = att_rect.bottom + 30

        # Instructions
        hint_surf = font_small.render(
            "Press SPACE to try again  |  R to restart level", True, WHITE
        )
        hint_rect = hint_surf.get_rect(centerx=cx, top=y)
        surface.blit(hint_surf, hint_rect)


# ---------------------------------------------------------------------------
# WinScreen
# ---------------------------------------------------------------------------

class WinScreen:
    """Shown when the player clears all levels."""

    def draw(
        self,
        surface: pygame.Surface,
        font_big: pygame.font.Font,
        font_small: pygame.font.Font,
        attempts: int,
        score: int,
    ):
        surface.fill(BLACK)

        cx = SCREEN_W // 2
        y = SCREEN_H // 5

        # "YOU WIN!"
        win_surf = font_big.render("YOU WIN!", True, YELLOW)
        win_rect = win_surf.get_rect(centerx=cx, top=y)
        surface.blit(win_surf, win_rect)
        y = win_rect.bottom + 30

        # Score
        score_surf = font_small.render(f"Score: {score}", True, WHITE)
        score_rect = score_surf.get_rect(centerx=cx, top=y)
        surface.blit(score_surf, score_rect)
        y = score_rect.bottom + 12

        # Total attempts
        att_surf = font_small.render(f"Total attempts: {attempts}", True, WHITE)
        att_rect = att_surf.get_rect(centerx=cx, top=y)
        surface.blit(att_surf, att_rect)
        y = att_rect.bottom + 30

        # Play again
        again_surf = font_small.render("Press SPACE to play again", True, WHITE)
        again_rect = again_surf.get_rect(centerx=cx, top=y)
        surface.blit(again_surf, again_rect)


# ---------------------------------------------------------------------------
# LevelCompleteScreen
# ---------------------------------------------------------------------------

class LevelCompleteScreen:
    """Brief overlay shown between levels."""

    _OVERLAY_ALPHA = 180

    def draw(
        self,
        surface: pygame.Surface,
        font_big: pygame.font.Font,
        font_small: pygame.font.Font,
        level_num: int,
        attempts: int,
    ):
        # Semi-transparent overlay so the level is still visible underneath
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self._OVERLAY_ALPHA))
        surface.blit(overlay, (0, 0))

        cx = SCREEN_W // 2
        y = SCREEN_H // 3

        # "Level N Complete!"
        complete_surf = font_big.render(f"Level {level_num} Complete!", True, YELLOW)
        complete_rect = complete_surf.get_rect(centerx=cx, top=y)
        surface.blit(complete_surf, complete_rect)
        y = complete_rect.bottom + 20

        # Attempts this level
        att_surf = font_small.render(f"Attempts this level: {attempts}", True, WHITE)
        att_rect = att_surf.get_rect(centerx=cx, top=y)
        surface.blit(att_surf, att_rect)
        y = att_rect.bottom + 24

        # Continue
        cont_surf = font_small.render("Press SPACE to continue", True, WHITE)
        cont_rect = cont_surf.get_rect(centerx=cx, top=y)
        surface.blit(cont_surf, cont_rect)


# ---------------------------------------------------------------------------
# UIManager — convenience wrapper
# ---------------------------------------------------------------------------

class UIManager:
    """Holds all UI components and fonts; exposes high-level draw helpers."""

    def __init__(self):
        pygame.font.init()

        # Fonts
        self.font_big   = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_med   = pygame.font.SysFont("Arial", 36)
        self.font_small = pygame.font.SysFont("Arial", 24)

        # Components
        self.hud            = HUD(self.font_small)
        self.death_msg      = DeathMessage()
        self.menu           = MenuScreen()
        self.death_screen   = DeathScreen()
        self.win_screen     = WinScreen()
        self.level_complete = LevelCompleteScreen()

        # Currently active death message text
        self._current_msg: str = ""

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def new_death_message(self) -> str:
        """Pick a fresh death message and cache it.  Returns the string."""
        self._current_msg = self.death_msg.pick()
        return self._current_msg

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------

    def draw_hud(
        self,
        surface: pygame.Surface,
        level_num: int,
        attempts: int,
        score: int,
        checkpoint_saved: bool = False,
        checkpoint_flash: bool = False,
        **kwargs,
    ):
        self.hud.draw(
            surface,
            level_num,
            attempts,
            score,
            checkpoint_saved=checkpoint_saved,
            checkpoint_flash=checkpoint_flash,
            **kwargs,
        )

    def draw_menu(self, surface: pygame.Surface):
        self.menu.draw(surface, self.font_big, self.font_small)

    def draw_death(self, surface: pygame.Surface, attempts: int):
        self.death_screen.draw(
            surface,
            self.font_big,
            self.font_small,
            attempts,
            self._current_msg,
            font_med=self.font_med,
        )

    def draw_win(self, surface: pygame.Surface, attempts: int, score: int):
        self.win_screen.draw(surface, self.font_big, self.font_small, attempts, score)

    def draw_level_complete(self, surface: pygame.Surface, level_num: int, attempts: int):
        self.level_complete.draw(surface, self.font_big, self.font_small, level_num, attempts)
