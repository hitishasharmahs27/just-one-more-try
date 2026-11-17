"""
level.py — Level loading and management for 'Just One More Try'.

Loads 28×18 tilemaps, tracks categorized tile rects (platforms, hazards,
checkpoints, goal, slippery, vanishing, invisible), and manages level transitions.
"""

import os
import pygame
from settings import TILE_SIZE, SCREEN_W, SCREEN_H
from settings import TROLL_VANISH_DELAY_S, TROLL_VANISH_RESPAWN_S, LEVEL_DIFFICULTY


# ---------------------------------------------------------------------------
# Tile character constants (matches level file legend)
# ---------------------------------------------------------------------------
TILE_AIR        = '.'
TILE_SOLID      = '#'
TILE_HAZARD     = 'H'
TILE_CHECKPOINT = 'C'
TILE_GOAL       = 'G'
TILE_SPAWN      = 'S'
TILE_SLIPPERY   = 's'
TILE_VANISHING  = 'V'
TILE_INVISIBLE  = 'I'


def _tile_rect(col: int, row: int) -> pygame.Rect:
    """Return pixel rect for a tile at grid position (col, row)."""
    return pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)


# ---------------------------------------------------------------------------
# Support classes for cross-module compatibility
# ---------------------------------------------------------------------------

class VanishingTile(dict):
    """
    Vanishing platform tile.
    Operates as a dictionary ({'rect': ..., 'state': ..., 'timer': ..., 'touched': ...})
    for troll.py and tests, while providing attribute access (.rect, .state,
    .timer, .vanish_delay, .touched) for game.py rendering.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        state: str = 'solid',
        timer: float = 0.0,
        touched: bool = False,
    ) -> None:
        super().__init__(rect=rect, state=state, timer=timer, touched=touched)

    @property
    def rect(self) -> pygame.Rect:
        return self['rect']

    @rect.setter
    def rect(self, val: pygame.Rect) -> None:
        self['rect'] = val

    @property
    def state(self) -> str:
        return self['state']

    @state.setter
    def state(self, val: str) -> None:
        self['state'] = val

    @property
    def timer(self) -> float:
        return self['timer']

    @timer.setter
    def timer(self, val: float) -> None:
        self['timer'] = val

    @property
    def touched(self) -> bool:
        return self['touched']

    @touched.setter
    def touched(self, val: bool) -> None:
        self['touched'] = val

    @property
    def vanish_delay(self) -> float:
        return self.get('vanish_delay_override', TROLL_VANISH_DELAY_S)


class Checkpoint(pygame.Rect):
    """
    Checkpoint tile bounding box. Subclasses pygame.Rect directly so it passes
    colliderect queries, while exposing .rect -> self for callers that access cp.rect.
    """

    @property
    def rect(self) -> pygame.Rect:
        return self

    def copy(self) -> 'Checkpoint':
        return Checkpoint(self.x, self.y, self.width, self.height)


# ---------------------------------------------------------------------------
# class Level
# ---------------------------------------------------------------------------

class Level:
    """
    Loads a single level from a text file and exposes categorised tile lists
    for rendering and physics.

    File format:
        Line 0 : trolls:<name1>,<name2>,...
        Lines 1+: 28-character rows of tile characters (18 rows)
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]  # e.g. "level1"

        # Parsed data ---------------------------------------------------------
        self.tile_map: list[list[str]] = []   # tile_map[row][col]
        self.active_trolls: list[str] = []

        # Physics / gameplay tile lists (rebuilt by reset()) ------------------
        self.platforms:       list[pygame.Rect]     = []  # #, s, C, G, S (walkable)
        self.slippery_tiles:  list[pygame.Rect]     = []  # s tiles
        self.vanishing_tiles: list[VanishingTile]   = []  # dicts with attributes
        self.invisible_tiles: list[pygame.Rect]     = []  # I tiles
        self.hazards:         list[pygame.Rect]     = []  # H tiles
        self.checkpoints:     list[Checkpoint]      = []  # C tiles (ordered)
        self.goal:            pygame.Rect | None    = None
        self.spawn:           tuple[float, float]   = (0.0, 0.0)  # px centre

        self._load(path)

    @property
    def vanishing_platforms(self) -> list[VanishingTile]:
        """Alias for game.py rendering loop."""
        return self.vanishing_tiles

    @property
    def invisible_platforms(self) -> list[pygame.Rect]:
        """Alias for game.py rendering loop."""
        return self.invisible_tiles

    # ------------------------------------------------------------------
    # Private loading helpers
    # ------------------------------------------------------------------

    def _load(self, path: str) -> None:
        with open(path, 'r', encoding='utf-8') as fh:
            lines = [ln.rstrip('\r\n') for ln in fh.readlines()]

        if not lines:
            raise ValueError(f"Level file is empty: {path}")

        # --- Header -------------------------------------------------------
        header = lines[0]
        if not header.startswith('trolls:'):
            raise ValueError(f"Level header must start with 'trolls:' — got: {header!r}")
        troll_part = header[len('trolls:'):]
        self.active_trolls = [t.strip() for t in troll_part.split(',') if t.strip()]

        # --- Grid ---------------------------------------------------------
        grid_lines = lines[1:]
        self.tile_map = [list(row) for row in grid_lines]
        self._build_tile_lists()

    def _build_tile_lists(self) -> None:
        """Scan tile_map and populate all categorised tile lists."""
        self.platforms       = []
        self.slippery_tiles  = []
        self.vanishing_tiles = []
        self.invisible_tiles = []
        self.hazards         = []
        self.checkpoints     = []
        self.goal            = None

        for row_idx, row in enumerate(self.tile_map):
            for col_idx, ch in enumerate(row):
                rect = _tile_rect(col_idx, row_idx)

                if ch == TILE_SOLID:
                    self.platforms.append(rect.copy())

                elif ch == TILE_SLIPPERY:
                    self.slippery_tiles.append(rect.copy())
                    self.platforms.append(rect.copy())

                elif ch == TILE_VANISHING:
                    self.vanishing_tiles.append(
                        VanishingTile(
                            rect=rect.copy(),
                            state='solid',
                            timer=0.0,
                            touched=False,
                        )
                    )

                elif ch == TILE_INVISIBLE:
                    self.invisible_tiles.append(rect.copy())

                elif ch == TILE_HAZARD:
                    self.hazards.append(rect.copy())

                elif ch == TILE_CHECKPOINT:
                    cp = Checkpoint(rect.x, rect.y, rect.width, rect.height)
                    self.checkpoints.append(cp)
                    self.platforms.append(rect.copy())

                elif ch == TILE_GOAL:
                    self.goal = rect.copy()
                    # Note: goal is an trigger area, not a solid wall,
                    # so the player can enter it to complete the level.

                elif ch == TILE_SPAWN:
                    cx = col_idx * TILE_SIZE + TILE_SIZE // 2
                    cy = row_idx * TILE_SIZE + TILE_SIZE // 2
                    self.spawn = (float(cx), float(cy))
                    self.platforms.append(rect.copy())

    # ------------------------------------------------------------------
    # Public API expected by Game / Player / TrollEngine
    # ------------------------------------------------------------------

    def get_solid_rects(self) -> list[pygame.Rect]:
        """
        Return every rect the player can collide with this frame.
        Includes: platforms, slippery tiles, invisible tiles, and
        currently 'solid' vanishing tiles.
        """
        solid_vanishing = [
            vt['rect'] for vt in self.vanishing_tiles if vt['state'] == 'solid'
        ]
        # Platforms already includes solid characters; slippery tiles, invisible
        # tiles, and active vanishing tiles complete the walkable set.
        return (
            self.platforms
            + self.slippery_tiles
            + self.invisible_tiles
            + solid_vanishing
        )

    def update_vanishing(self, dt: float, troll_active: bool) -> None:
        """
        Advance vanishing platform state machine when troll_active is True.
        """
        if not troll_active:
            return
        for vt in self.vanishing_tiles:
            delay = vt.get('vanish_delay_override', TROLL_VANISH_DELAY_S)
            if vt['state'] == 'vanishing':
                vt['timer'] += dt
                if vt['timer'] >= delay:
                    vt['state'] = 'gone'
                    vt['timer'] = 0.0
            elif vt['state'] == 'gone':
                vt['timer'] += dt
                if vt['timer'] >= TROLL_VANISH_RESPAWN_S:
                    vt['state']   = 'solid'
                    vt['timer']   = 0.0
                    vt['touched'] = False

    def set_difficulty(self, level_num: int) -> None:
        """Scale level-specific parameters (like vanishing platform timers) with difficulty."""
        diff = LEVEL_DIFFICULTY.get(level_num, {})
        v_delay = diff.get('vanish_delay_s', TROLL_VANISH_DELAY_S)
        for vt in self.vanishing_tiles:
            vt['vanish_delay_override'] = v_delay

    def notify_vanishing_touched(self, rect: pygame.Rect) -> None:
        """
        Called when a vanishing tile is touched.
        Supports passing either the tile's exact rect or the player's bounding rect.
        """
        for vt in self.vanishing_tiles:
            if vt['state'] == 'solid':
                # Exact match or player standing on top / overlapping
                is_match = (
                    vt['rect'] == rect
                    or vt['rect'].colliderect(rect)
                    or vt['rect'].colliderect(rect.move(0, 2))
                )
                if is_match:
                    vt['state']   = 'vanishing'
                    vt['timer']   = 0.0
                    vt['touched'] = True
                    break

    def reset(self) -> None:
        """
        Reset all vanishing tiles to 'solid' and rebuild the platform list
        from the tile_map so original geometry is fully restored.
        """
        for vt in self.vanishing_tiles:
            vt['state']   = 'solid'
            vt['timer']   = 0.0
            vt['touched'] = False

        self._build_tile_lists()


# ---------------------------------------------------------------------------
# class LevelManager
# ---------------------------------------------------------------------------

class LevelManager:
    """
    Sequences and loads levels in order.

    Usage::
        lm = LevelManager(['levels/level1.txt', ..., 'levels/level5.txt'])
        level = lm.load(0)
        next_lvl = lm.next_level()
    """

    def __init__(self, level_paths: list[str]) -> None:
        self.paths: list[str] = list(level_paths)
        self.current_index: int = -1
        self.current_level: Level | None = None

    def load(self, index: int) -> Level:
        """Load level at *index* and return it."""
        if index < 0 or index >= len(self.paths):
            raise IndexError(f"Level index {index} out of range (0–{len(self.paths)-1})")
        self.current_index = index
        self.current_level = Level(self.paths[index])
        return self.current_level

    def next_level(self) -> Level | None:
        """
        Advance to the next level and return it, or return None if all
        levels are complete.
        """
        next_index = self.current_index + 1
        if next_index < len(self.paths):
            return self.load(next_index)
        return None
