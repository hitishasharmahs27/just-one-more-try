"""
player.py — Player Controller for 'Just One More Try'

Owns: position, velocity, input handling, respawn, and checkpoint tracking.
The Troll Engine wires into the player via the hooks dict (callables by name).
This module does NOT import troll.py.
"""

import pygame
from settings import (
    WALK_SPEED, JUMP_SPEED, GRAVITY, MAX_FALL_SPEED, FIXED_DT,
    GROUND_FRICTION, AIR_FRICTION, TROLL_SLIPPERY_FRICTION_MULT,
    TILE_SIZE,
)
from physics import apply_gravity, resolve_x, resolve_y, near_slippery_edge


class Player:
    """
    The player character.

    Position (self.x, self.y) is the top-left corner of the player's bounding
    box, stored as floats for sub-pixel accuracy. Collision uses pygame.Rect
    conversions of those floats.

    Hooks (injected by TrollEngine) are optional callables keyed by name:
        on_input(raw_keys: dict, dt: float) -> (dict, float)
        on_jump(base_jump_speed: float) -> float
        on_update(player, dt: float) -> None
        on_checkpoint(index: int) -> bool   # True = saved, False = failed troll
    """

    def __init__(self, spawn_px: tuple[int, int], hooks: dict | None = None):
        # Position (top-left, float px)
        self.x: float = float(spawn_px[0])
        self.y: float = float(spawn_px[1])

        # Velocity (px / s)
        self.vx: float = 0.0
        self.vy: float = 0.0

        # Size — slight inset from tile so the player can fit into passages
        self.width: int = TILE_SIZE - 4
        self.height: int = TILE_SIZE - 4

        # State
        self.on_ground: bool = False
        self.alive: bool = True

        # Spawn / checkpoint positions
        self.spawn: tuple[int, int] = spawn_px
        self.checkpoint_spawn: tuple[int, int] = spawn_px
        self.last_checkpoint_idx: int = -1

        # Troll Engine hooks (must not be None)
        self._hooks: dict = hooks if hooks is not None else {}

        # Input queue — used by the input-delay troll
        self._input_queue: list = []

        # Seconds elapsed since the level started (for input-delay grace period)
        self._level_time: float = 0.0

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    @property
    def rect(self) -> pygame.Rect:
        """Return the player's bounding box as a pygame.Rect."""
        return self.get_rect()

    def get_rect(self) -> pygame.Rect:
        """Return the player's bounding box as a pygame.Rect."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, raw_keys, dt: float) -> None:
        """
        Read keyboard state, apply optional troll hook, then set velocity.

        Parameters
        ----------
        raw_keys:
            Whatever pygame.key.get_pressed() returns (a sequence indexed by
            K_* constants).
        dt:
            Delta time in seconds for this fixed-timestep tick.
        """
        # 1. Accumulate level time for the grace-period logic used by hooks.
        self._level_time += dt

        # 2. Build the action dict from the raw pygame key state.
        action_keys: dict = {
            'left':  bool(raw_keys[pygame.K_LEFT]  or raw_keys[pygame.K_a]),
            'right': bool(raw_keys[pygame.K_RIGHT] or raw_keys[pygame.K_d]),
            'jump':  bool(
                raw_keys[pygame.K_SPACE] or
                raw_keys[pygame.K_UP]    or
                raw_keys[pygame.K_w]
            ),
        }

        # 3. Let the troll hook modify (or delay) the keys.
        on_input = self._hooks.get('on_input')
        if on_input is not None:
            modified_keys, dt = on_input(action_keys, dt)
        else:
            modified_keys = action_keys

        # 4. Apply horizontal movement.
        moving_horizontally = False
        if modified_keys.get('left'):
            self.vx = -WALK_SPEED
            moving_horizontally = True
        elif modified_keys.get('right'):
            self.vx = WALK_SPEED
            moving_horizontally = True

        # 5. Apply friction when no horizontal input.
        if not moving_horizontally:
            friction = GROUND_FRICTION if self.on_ground else AIR_FRICTION
            self.vx *= friction

        # 6. Jump.
        if modified_keys.get('jump') and self.on_ground:
            on_jump = self._hooks.get('on_jump')
            if on_jump is not None:
                jump_speed = on_jump(JUMP_SPEED)
            else:
                jump_speed = JUMP_SPEED
            self.vy = jump_speed
            self.on_ground = False

    # ------------------------------------------------------------------
    # Physics update
    # ------------------------------------------------------------------

    def update(
        self,
        dt: float,
        solid_rects: list,
        hazard_rects: list,
        checkpoint_rects: list,
        goal_rect,
        slippery_rects: list,
        level,
    ) -> str:
        """
        Advance physics, resolve collisions, and check game triggers.

        Returns
        -------
        str
            One of: 'playing', 'dead', 'checkpoint', 'goal'.
        """
        # 1. Apply gravity.
        self.vy = apply_gravity(self.vy, dt)

        # 2. Cap fall speed.
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        # 3. Resolve horizontal movement.
        new_rect, new_vx, _hit_wall = resolve_x(self.get_rect(), solid_rects, self.vx, dt)
        self.x = float(new_rect.x)
        self.vx = new_vx

        # 4. Resolve vertical movement.
        new_rect, new_vy, on_ground = resolve_y(self.get_rect(), solid_rects, self.vy, dt)
        self.y = float(new_rect.y)
        self.vy = new_vy
        self.on_ground = on_ground

        # 5. Notify vanishing tiles when the player lands on one.
        if self.on_ground and hasattr(level, 'notify_vanishing_touched'):
            level.notify_vanishing_touched(self.get_rect())

        # 6. Slippery-edge friction (applied while on_ground near a slippery tile).
        if self.on_ground and near_slippery_edge(self.get_rect(), slippery_rects):
            self.vx *= TROLL_SLIPPERY_FRICTION_MULT

        # 7. Generic troll per-tick hook (misc effects, e.g. fake wall spam).
        on_update = self._hooks.get('on_update')
        if on_update is not None:
            on_update(player=self, dt=dt)

        # 8. Hazard check — instant death.
        if self._check_hazards(hazard_rects):
            self.alive = False
            return 'dead'

        # 9. Checkpoint check.
        checkpoint_result = self._check_checkpoints(checkpoint_rects)
        if checkpoint_result is not None:
            return checkpoint_result

        # 10. Goal check.
        if self._check_goal(goal_rect):
            return 'goal'

        return 'playing'

    # ------------------------------------------------------------------
    # Trigger helpers
    # ------------------------------------------------------------------

    def _check_hazards(self, hazard_rects: list) -> bool:
        """Return True if the player is touching any hazard rect."""
        player_rect = self.get_rect()
        for hrect in hazard_rects:
            if player_rect.colliderect(hrect):
                return True
        return False

    def _check_checkpoints(self, checkpoint_rects: list) -> str | None:
        """
        Return 'checkpoint' if a new checkpoint was saved, None otherwise.
        Calls the on_checkpoint hook which may (troll) refuse the save.
        """
        player_rect = self.get_rect()
        for index, crect in enumerate(checkpoint_rects):
            if player_rect.colliderect(crect):
                on_checkpoint = self._hooks.get('on_checkpoint')
                if on_checkpoint is not None:
                    saved = on_checkpoint(index)
                else:
                    saved = True

                if saved:
                    # Store the checkpoint tile centre as the new respawn point.
                    self.checkpoint_spawn = (crect.x, crect.y)
                    self.last_checkpoint_idx = index
                    return 'checkpoint'
        return None

    def _check_goal(self, goal_rect) -> bool:
        """Return True if the player has reached the goal."""
        if goal_rect is None:
            return False
        return self.get_rect().colliderect(goal_rect)

    # ------------------------------------------------------------------
    # Respawn
    # ------------------------------------------------------------------

    def respawn(self) -> None:
        """
        Respawn at the last saved checkpoint.
        Resets position, velocity and aliveness, but keeps checkpoint_spawn.
        """
        self.x = float(self.checkpoint_spawn[0])
        self.y = float(self.checkpoint_spawn[1])
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self._level_time = 0.0

    def full_respawn(self) -> None:
        """
        Full level restart — resets everything including checkpoint progress.
        """
        self.checkpoint_spawn = self.spawn
        self.last_checkpoint_idx = -1
        self.respawn()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def set_level_time(self, t: float) -> None:
        """Allow external callers (e.g. TrollEngine) to set the level timer."""
        self._level_time = t

    def __repr__(self) -> str:
        return (
            f"<Player x={self.x:.1f} y={self.y:.1f} "
            f"vx={self.vx:.1f} vy={self.vy:.1f} "
            f"on_ground={self.on_ground} alive={self.alive}>"
        )
