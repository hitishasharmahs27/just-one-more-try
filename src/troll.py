import random
import collections
import time
import pygame
from settings import (
    TROLL_RANDOM_SEED, TROLL_JUMP_FACTOR_MIN, TROLL_JUMP_FACTOR_MAX, TROLL_JUMP_MIN_SAFE,
    TROLL_INPUT_DELAY_MIN_MS, TROLL_INPUT_DELAY_MAX_MS,
    TROLL_INPUT_DELAY_GRACE_S, TROLL_INPUT_DELAY_CHANCE,
    TROLL_CHECKPOINT_FAIL_CHANCE, TROLL_CHECKPOINT_NEVER_TWICE,
    TROLL_SLIPPERY_FRICTION_MULT,
    TROLL_VANISH_DELAY_S, TROLL_VANISH_RESPAWN_S,
    LEVEL_DIFFICULTY,
    JUMP_SPEED, DEBUG
)


class TrollModifier:
    name: str = "base"
    enabled: bool = True

    def on_input(self, action_keys, dt):
        return action_keys, dt

    def on_jump(self, base_jump_speed):
        return base_jump_speed

    def on_land(self, player):
        pass

    def on_checkpoint(self, index):
        return True  # True = save succeeded

    def on_update(self, player, dt):
        pass

    def on_draw(self, surface, camera_offset=(0, 0)):
        pass

    def reset(self):
        pass


class VariableJump(TrollModifier):
    name = "variable_jump"

    def __init__(self):
        super().__init__()
        self.factor_min = TROLL_JUMP_FACTOR_MIN
        self.factor_max = TROLL_JUMP_FACTOR_MAX

    def on_jump(self, base_jump_speed):
        scaled = base_jump_speed * self.rng.uniform(self.factor_min, self.factor_max)
        # Note: In Pygame, upward velocity is negative (JUMP_SPEED = -680.0).
        if base_jump_speed < 0:
            min_speed = JUMP_SPEED * TROLL_JUMP_MIN_SAFE
            # Guardrail: jump must be at least as strong as min_speed (i.e. <= min_speed).
            return min(scaled, min_speed)
        else:
            min_speed = abs(JUMP_SPEED) * TROLL_JUMP_MIN_SAFE
            return max(scaled, min_speed)


class InputDelay(TrollModifier):
    name = "input_delay"

    def __init__(self):
        super().__init__()
        self._queue = collections.deque()
        self._level_time = 0.0
        self.delay_min_ms = TROLL_INPUT_DELAY_MIN_MS
        self.delay_max_ms = TROLL_INPUT_DELAY_MAX_MS
        self.delay_chance = TROLL_INPUT_DELAY_CHANCE
        self.delay_grace_s = TROLL_INPUT_DELAY_GRACE_S

    def on_input(self, action_keys, dt):
        self._level_time += dt
        # Use player-provided _level_time if present, else internal tracked time
        level_time = action_keys.get('_level_time', self._level_time)

        # Grace period: pass through unmodified
        if level_time < self.delay_grace_s:
            return action_keys, dt

        try:
            now_ms = pygame.time.get_ticks()
        except Exception:
            now_ms = int(time.time() * 1000)

        # Possibly delay the jump
        modified_keys = dict(action_keys)
        if modified_keys.get('jump') and self.rng.random() < self.delay_chance:
            delay_ms = self.rng.randint(self.delay_min_ms, self.delay_max_ms)
            # Schedule the real jump for later
            delayed_keys = dict(action_keys)
            delayed_keys['jump'] = True
            self._queue.append((now_ms + delay_ms, delayed_keys))
            # Suppress jump for now
            modified_keys['jump'] = False

        # Drain queue: apply any delayed jumps whose time has come
        while self._queue:
            release_time, queued_keys = self._queue[0]
            if release_time <= now_ms:
                self._queue.popleft()
                # Merge jump=True back into modified_keys
                modified_keys['jump'] = True
            else:
                break

        return modified_keys, dt

    def reset(self):
        self._queue.clear()
        self._level_time = 0.0


class UnreliableCheckpoints(TrollModifier):
    name = "unreliable_checkpoints"

    def __init__(self):
        super().__init__()
        self._last_failed = False
        self.fail_chance = TROLL_CHECKPOINT_FAIL_CHANCE

    def on_checkpoint(self, index):
        # If NEVER_TWICE is set, don't fail twice in a row
        if TROLL_CHECKPOINT_NEVER_TWICE and self._last_failed:
            self._last_failed = False
            return True

        if self.rng.random() < self.fail_chance:
            self._last_failed = True
            return False  # checkpoint fails to save
        else:
            self._last_failed = False
            return True

    def reset(self):
        self._last_failed = False


class SlipperyEdges(TrollModifier):
    """
    Slippery-edge logic lives in physics.py (near_slippery_edge()) and
    player.py (friction application).  This class exists only for
    registration and toggling via TrollEngine.
    """
    name = "slippery_edges"

    def on_update(self, player, dt):
        pass  # no-op; real work is in physics/player


class VanishingPlatforms(TrollModifier):
    name = "vanishing_platforms"

    def __init__(self):
        super().__init__()
        self._level = None

    def set_level(self, level):
        self._level = level

    def on_update(self, player, dt):
        # Driven from game.py via level.update_vanishing() to avoid double update
        pass

    def on_draw(self, surface, camera_offset=(0, 0)):
        if self._level is None:
            return

        for vt in self._level.vanishing_tiles:
            if vt['state'] == 'vanishing':
                rect = vt['rect']
                # Remaining time determines alpha (fade out as time runs down)
                elapsed = vt.get('elapsed', 0)
                total = TROLL_VANISH_DELAY_S
                remaining_ratio = max(0.0, 1.0 - (elapsed / total)) if total > 0 else 0.0
                alpha = int(255 * remaining_ratio)

                draw_rect = pygame.Rect(
                    rect.x - camera_offset[0],
                    rect.y - camera_offset[1],
                    rect.width,
                    rect.height
                )

                tile_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                # Draw with flicker: randomly reduce alpha for a flicker effect
                flicker = self.rng.randint(0, 40) if alpha > 40 else 0
                tile_surf.fill((180, 140, 80, max(0, alpha - flicker)))
                surface.blit(tile_surf, draw_rect)


class TrollEngine:
    def __init__(self, seed=TROLL_RANDOM_SEED):
        self.rng = random.Random(seed)
        self._registry: dict[str, TrollModifier] = {}
        self._active_names: list[str] = []
        # Instantiate all modifiers and share the rng
        self._all = [
            VariableJump(),
            InputDelay(),
            UnreliableCheckpoints(),
            SlipperyEdges(),
            VanishingPlatforms(),
        ]
        for m in self._all:
            m.rng = self.rng
            self._registry[m.name] = m

    def set_active(self, names: list):
        self._active_names = [n for n in names if n in self._registry]
        for m in self._all:
            m.enabled = (m.name in self._active_names)

    def apply_difficulty(self, level_num: int):
        """Tune modifier hardness parameters based on the current level."""
        diff = LEVEL_DIFFICULTY.get(level_num, LEVEL_DIFFICULTY.get(1, {}))
        if 'variable_jump' in self._registry:
            vj = self._registry['variable_jump']
            vj.factor_min = diff.get('jump_min', vj.factor_min)
            vj.factor_max = diff.get('jump_max', vj.factor_max)

        if 'input_delay' in self._registry:
            idly = self._registry['input_delay']
            idly.delay_min_ms = diff.get('delay_min_ms', idly.delay_min_ms)
            idly.delay_max_ms = diff.get('delay_max_ms', idly.delay_max_ms)
            idly.delay_chance = diff.get('delay_chance', idly.delay_chance)
            idly.delay_grace_s = diff.get('delay_grace', idly.delay_grace_s)

        if 'unreliable_checkpoints' in self._registry:
            ucp = self._registry['unreliable_checkpoints']
            ucp.fail_chance = diff.get('checkpoint_fail_chance', ucp.fail_chance)

    def _active_mods(self):
        return [m for m in self._all if m.enabled]

    def get_hooks(self) -> dict:
        """Return a hooks dict for the Player to call."""
        engine = self

        def on_input(action_keys, dt):
            for m in engine._active_mods():
                action_keys, dt = m.on_input(action_keys, dt)
            return action_keys, dt

        def on_jump(base_speed):
            for m in engine._active_mods():
                base_speed = m.on_jump(base_speed)
            return base_speed

        def on_land(player):
            for m in engine._active_mods():
                m.on_land(player)

        def on_checkpoint(index):
            results = [
                m.on_checkpoint(index)
                for m in engine._active_mods()
                if hasattr(m, 'on_checkpoint')
            ]
            return all(r for r in results) if results else True

        def on_update(player, dt):
            for m in engine._active_mods():
                m.on_update(player, dt)

        return {
            'on_input': on_input,
            'on_jump': on_jump,
            'on_land': on_land,
            'on_checkpoint': on_checkpoint,
            'on_update': on_update,
        }

    def draw(self, surface, camera_offset=(0, 0)):
        for m in self._active_mods():
            m.on_draw(surface, camera_offset)

    def on_update(self, *args, **kwargs):
        """Update active modifiers. Handles both on_update(dt) and on_update(player, dt)."""
        player = None
        dt = 0.0
        if len(args) == 1:
            if isinstance(args[0], (int, float)):
                dt = float(args[0])
            else:
                player = args[0]
        elif len(args) >= 2:
            player, dt = args[0], args[1]
        player = kwargs.get('player', player)
        dt = kwargs.get('dt', dt)
        for m in self._active_mods():
            m.on_update(player, dt)

    def reset(self):
        for m in self._all:
            m.reset()

    def toggle(self, name: str):
        if name in self._registry:
            m = self._registry[name]
            m.enabled = not m.enabled

    def set_level(self, level):
        for m in self._all:
            if hasattr(m, 'set_level'):
                m.set_level(level)
