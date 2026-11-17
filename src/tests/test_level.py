"""
test_level.py — Unit tests for level loading and LevelManager in level.py

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

from level import Level, LevelManager

LEVELS_DIR = str(SRC_DIR / 'levels')


# ---------------------------------------------------------------------------
# Level Loading Tests
# ---------------------------------------------------------------------------

class TestLevelLoading:
    def test_level_load(self):
        """
        Load level1.txt from the levels/ dir;
        check spawn is set, goal is set, len(platforms) > 0,
        and active_trolls == ['variable_jump'].
        """
        path = os.path.join(LEVELS_DIR, "level1.txt")
        lvl = Level(path)

        assert lvl.spawn is not None and lvl.spawn != (0.0, 0.0), "Spawn position not set"
        assert lvl.goal is not None, "Goal rect not set"
        assert len(lvl.platforms) > 0, "Level has no platforms"
        assert lvl.active_trolls == ['variable_jump'], (
            f"Expected active_trolls == ['variable_jump'], got {lvl.active_trolls}"
        )

    @pytest.mark.parametrize("level_num", [2, 3, 4, 5])
    def test_level_has_min_checkpoints(self, level_num):
        """
        Load levels 2-5, check each has at least 2 checkpoints (≥ 2).
        """
        path = os.path.join(LEVELS_DIR, f"level{level_num}.txt")
        lvl = Level(path)
        assert len(lvl.checkpoints) >= 2, (
            f"Level {level_num} has {len(lvl.checkpoints)} checkpoints, expected >= 2"
        )

    @pytest.mark.parametrize("level_num", [1, 2, 3, 4, 5])
    def test_all_levels_load(self, level_num):
        """
        Load all 5 levels, none raise exceptions; each has spawn and goal.
        """
        path = os.path.join(LEVELS_DIR, f"level{level_num}.txt")
        lvl = Level(path)
        assert lvl.spawn is not None
        assert lvl.goal is not None
        assert len(lvl.platforms) > 0


# ---------------------------------------------------------------------------
# Vanishing Platforms Reset Test
# ---------------------------------------------------------------------------

class TestVanishingPlatforms:
    def test_level_reset_vanishing(self):
        """
        Load level5.txt; for each vanishing tile, manually set state='gone';
        call level.reset(); check all reset back to 'solid'.
        """
        path = os.path.join(LEVELS_DIR, "level5.txt")
        lvl = Level(path)
        assert len(lvl.vanishing_tiles) > 0, "Level 5 must contain vanishing tiles ('V')"

        # Force state to 'gone'
        for vt in lvl.vanishing_tiles:
            vt['state'] = 'gone'
            vt['timer'] = 10.0
            vt['touched'] = True

        # Call reset
        lvl.reset()

        # Check all are back to solid
        for vt in lvl.vanishing_tiles:
            assert vt['state'] == 'solid', f"Tile state {vt['state']} != 'solid' after reset()"
            assert vt['timer'] == 0.0
            assert vt['touched'] is False


# ---------------------------------------------------------------------------
# LevelManager Tests
# ---------------------------------------------------------------------------

class TestLevelManager:
    def test_level_manager_next(self):
        """
        Create LevelManager, load(0), next_level() -> not None;
        call next_level() 4 more times until None.
        """
        paths = [os.path.join(LEVELS_DIR, f"level{i}.txt") for i in range(1, 6)]
        lm = LevelManager(paths)

        lvl0 = lm.load(0)
        assert lvl0 is not None
        assert lm.current_index == 0

        # Advance 4 more times (levels 1, 2, 3, 4 -> corresponding to levels 2..5)
        for expected_idx in range(1, 5):
            next_lvl = lm.next_level()
            assert next_lvl is not None, f"Expected level at index {expected_idx}, got None"
            assert lm.current_index == expected_idx

        # 5th call: beyond last level -> returns None
        last_call = lm.next_level()
        assert last_call is None, f"Expected None after final level, got {last_call}"

    def test_level_manager_invalid_index(self):
        """Loading an invalid index raises IndexError."""
        paths = [os.path.join(LEVELS_DIR, f"level{i}.txt") for i in range(1, 6)]
        lm = LevelManager(paths)
        with pytest.raises(IndexError):
            lm.load(-1)
        with pytest.raises(IndexError):
            lm.load(99)
