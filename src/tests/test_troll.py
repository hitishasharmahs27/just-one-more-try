"""
test_troll.py — Unit tests for troll mechanics in troll.py

Headless: SDL drivers set to dummy before importing pygame.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys
import pathlib
import pytest

SRC_DIR = pathlib.Path(__file__).parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from settings import (
    JUMP_SPEED,
    TROLL_RANDOM_SEED,
    TROLL_JUMP_FACTOR_MIN,
    TROLL_JUMP_FACTOR_MAX,
    TROLL_JUMP_MIN_SAFE,
    TROLL_INPUT_DELAY_GRACE_S,
)
from troll import (
    TrollEngine,
    VariableJump,
    InputDelay,
    UnreliableCheckpoints,
    SlipperyEdges,
    VanishingPlatforms,
)


# ---------------------------------------------------------------------------
# VariableJump Tests
# ---------------------------------------------------------------------------

class TestVariableJump:
    def test_variable_jump_within_range(self):
        """
        Call on_jump(JUMP_SPEED) 20 times with fixed seed (42).
        Since JUMP_SPEED is negative, more negative = higher jump.
        All results must fall between JUMP_SPEED * TROLL_JUMP_FACTOR_MAX (strongest)
        and JUMP_SPEED * TROLL_JUMP_MIN_SAFE (weakest safe jump).
        """
        engine = TrollEngine(seed=42)
        engine.set_active(['variable_jump'])
        hooks = engine.get_hooks()

        # Boundaries in negative velocity space
        strongest_jump = JUMP_SPEED * TROLL_JUMP_FACTOR_MAX   # e.g. -680 * 1.20 = -816
        weakest_safe   = JUMP_SPEED * TROLL_JUMP_MIN_SAFE     # e.g. -680 * 0.75 = -510

        for _ in range(20):
            res = hooks['on_jump'](JUMP_SPEED)
            # Result must be at least as strong as weakest_safe (res <= weakest_safe)
            # and no stronger than strongest_jump (res >= strongest_jump)
            assert strongest_jump - 1e-4 <= res <= weakest_safe + 1e-4, (
                f"Jump result {res} outside expected range [{strongest_jump}, {weakest_safe}]"
            )

    def test_variable_jump_min_safe(self):
        """
        Manually mock/set rng to return a scale factor of 0.5 (below min 0.80 and safe 0.75).
        Check that the guardrail kicks in and returns JUMP_SPEED * TROLL_JUMP_MIN_SAFE.
        """
        vj = VariableJump()
        # Mock rng.uniform to return 0.5 (unsafe weak factor)
        vj.rng = type('MockRng', (), {'uniform': lambda self, a, b: 0.5})()

        result = vj.on_jump(JUMP_SPEED)
        expected_min = JUMP_SPEED * TROLL_JUMP_MIN_SAFE  # -510.0
        assert result == pytest.approx(expected_min), (
            f"Expected guardrail jump {expected_min}, got {result}"
        )


# ---------------------------------------------------------------------------
# UnreliableCheckpoints Tests
# ---------------------------------------------------------------------------

class TestUnreliableCheckpoints:
    def test_unreliable_checkpoint_no_double_fail(self):
        """
        Calling on_checkpoint(0) repeatedly should NEVER produce two consecutive
        failures (False).
        """
        engine = TrollEngine(seed=42)
        engine.set_active(['unreliable_checkpoints'])
        hooks = engine.get_hooks()

        last_failed = False
        for _ in range(100):
            success = hooks['on_checkpoint'](0)
            if not success:
                assert not last_failed, "Checkpoints failed twice consecutively!"
                last_failed = True
            else:
                last_failed = False

    def test_unreliable_checkpoint_can_succeed(self):
        """At least one True in 10 calls."""
        engine = TrollEngine(seed=42)
        engine.set_active(['unreliable_checkpoints'])
        hooks = engine.get_hooks()

        results = [hooks['on_checkpoint'](0) for _ in range(10)]
        assert any(results), "Expected at least one checkpoint to succeed out of 10"


# ---------------------------------------------------------------------------
# TrollEngine Management Tests
# ---------------------------------------------------------------------------

class TestTrollEngine:
    def test_troll_engine_set_active(self):
        """
        Create TrollEngine, set_active(['variable_jump']),
        check only variable_jump is enabled and all others disabled.
        """
        engine = TrollEngine(seed=42)
        engine.set_active(['variable_jump'])

        assert engine._registry['variable_jump'].enabled is True
        for name, mod in engine._registry.items():
            if name != 'variable_jump':
                assert mod.enabled is False, f"Expected {name} to be disabled"

    def test_troll_engine_toggle(self):
        """
        Toggle 'variable_jump': check it disables, then toggle again and check enabled.
        """
        engine = TrollEngine(seed=42)
        engine.set_active(['variable_jump'])
        assert engine._registry['variable_jump'].enabled is True

        # Toggle once -> disabled
        engine.toggle('variable_jump')
        assert engine._registry['variable_jump'].enabled is False

        # Toggle again -> re-enabled
        engine.toggle('variable_jump')
        assert engine._registry['variable_jump'].enabled is True

    def test_troll_engine_inactive_returns_unmodified_jump(self):
        """When variable_jump is inactive, on_jump returns base_speed unchanged."""
        engine = TrollEngine(seed=42)
        engine.set_active([])
        hooks = engine.get_hooks()

        res = hooks['on_jump'](JUMP_SPEED)
        assert res == pytest.approx(JUMP_SPEED)

    def test_troll_engine_reset(self):
        """reset() calls reset on all modifiers without raising exceptions."""
        engine = TrollEngine(seed=42)
        engine.reset()  # should not throw
