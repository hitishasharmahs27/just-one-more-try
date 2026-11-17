"""
test_physics.py — Unit tests for physics.py

Headless: SDL drivers are forced to 'dummy' before any pygame import.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys
import pathlib
import pytest
import pygame

# Ensure src/ is importable
SRC_DIR = pathlib.Path(__file__).parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from settings import GRAVITY, MAX_FALL_SPEED, FIXED_DT
import physics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rect(x=0, y=0, w=32, h=48) -> pygame.Rect:
    return pygame.Rect(x, y, w, h)


# ---------------------------------------------------------------------------
# apply_gravity
# ---------------------------------------------------------------------------

class TestApplyGravity:
    def test_apply_gravity_zero_increases(self):
        """Starting from vy=0 gravity must push vy positive (downward)."""
        result = physics.apply_gravity(0.0)
        assert result > 0.0

    def test_apply_gravity_uses_dt(self):
        """Result should equal vy + GRAVITY * dt."""
        vy = 100.0
        dt = 0.02
        expected = min(vy + GRAVITY * dt, MAX_FALL_SPEED)
        assert physics.apply_gravity(vy, dt) == pytest.approx(expected)

    def test_apply_gravity_capped_at_max(self):
        """vy just below MAX_FALL_SPEED should be capped, not exceeded."""
        vy = MAX_FALL_SPEED - 1.0
        result = physics.apply_gravity(vy)
        assert result <= MAX_FALL_SPEED

    def test_apply_gravity_already_at_max(self):
        """vy already at MAX_FALL_SPEED stays at MAX_FALL_SPEED."""
        result = physics.apply_gravity(MAX_FALL_SPEED)
        assert result == pytest.approx(MAX_FALL_SPEED)

    def test_apply_gravity_negative_vy_increases(self):
        """Negative vy (upward) is pulled toward zero by gravity."""
        result = physics.apply_gravity(-100.0)
        assert result > -100.0


# ---------------------------------------------------------------------------
# resolve_x
# ---------------------------------------------------------------------------

class TestResolveX:
    def test_resolve_x_no_collision(self):
        """Entity moving right with no tiles moves freely, no wall hit."""
        entity = make_rect(0, 0, 32, 48)
        new_rect, new_vx, hit_wall = physics.resolve_x(entity, [], 200.0)
        # Should have moved right
        assert new_rect.x > 0
        assert new_vx == pytest.approx(200.0)
        assert hit_wall is False

    def test_resolve_x_wall_stop_right(self):
        """Entity moving right into a wall is stopped; hit_wall is True."""
        entity = make_rect(0, 0, 32, 48)
        wall = pygame.Rect(30, 0, 48, 48)   # close enough to collide after move
        new_rect, new_vx, hit_wall = physics.resolve_x(entity, [wall], 500.0)
        assert hit_wall is True
        assert new_vx == pytest.approx(0.0)
        # Right edge must be flush with wall left
        assert new_rect.right == wall.left

    def test_resolve_x_wall_stop_left(self):
        """Entity moving left into a wall is stopped; hit_wall is True."""
        entity = make_rect(100, 0, 32, 48)
        wall = pygame.Rect(50, 0, 48, 48)
        new_rect, new_vx, hit_wall = physics.resolve_x(entity, [wall], -500.0)
        assert hit_wall is True
        assert new_vx == pytest.approx(0.0)
        assert new_rect.left == wall.right

    def test_resolve_x_no_move_when_vx_zero(self):
        """Zero velocity → rect stays in place."""
        entity = make_rect(100, 100, 32, 48)
        new_rect, new_vx, hit_wall = physics.resolve_x(entity, [], 0.0)
        assert new_rect.x == entity.x
        assert hit_wall is False

    def test_resolve_x_does_not_mutate_input(self):
        """Original entity rect must not be modified."""
        entity = make_rect(0, 0, 32, 48)
        original_x = entity.x
        physics.resolve_x(entity, [], 200.0)
        assert entity.x == original_x


# ---------------------------------------------------------------------------
# resolve_y
# ---------------------------------------------------------------------------

class TestResolveY:
    def test_resolve_y_landing(self):
        """Entity falling onto a platform → on_ground=True, vy=0."""
        entity = make_rect(100, 0, 32, 48)
        platform = pygame.Rect(80, 40, 100, 48)   # entity will fall into it
        new_rect, new_vy, on_ground = physics.resolve_y(entity, [platform], 2000.0)
        assert on_ground is True
        assert new_vy == pytest.approx(0.0)
        assert new_rect.bottom == platform.top

    def test_resolve_y_ceiling(self):
        """Entity moving up into a ceiling → vy reset, on_ground=False."""
        # Entity below a ceiling tile, moving up fast
        entity = make_rect(100, 100, 32, 48)
        ceiling = pygame.Rect(80, 60, 100, 48)
        new_rect, new_vy, on_ground = physics.resolve_y(entity, [ceiling], -2000.0)
        assert on_ground is False
        assert new_vy == pytest.approx(0.0)
        # Entity top must have been pushed to ceiling bottom
        assert new_rect.top == ceiling.bottom

    def test_resolve_y_no_collision(self):
        """Entity falling with no tiles moves freely."""
        entity = make_rect(0, 0, 32, 48)
        new_rect, new_vy, on_ground = physics.resolve_y(entity, [], 300.0)
        assert new_rect.y > 0
        assert on_ground is False
        assert new_vy == pytest.approx(300.0)

    def test_resolve_y_does_not_mutate_input(self):
        """Original entity rect must not be modified."""
        entity = make_rect(0, 0, 32, 48)
        original_y = entity.y
        physics.resolve_y(entity, [], 200.0)
        assert entity.y == original_y


# ---------------------------------------------------------------------------
# overlap
# ---------------------------------------------------------------------------

class TestOverlap:
    def test_overlap_true(self):
        """Two overlapping rects → True."""
        a = pygame.Rect(0, 0, 50, 50)
        b = pygame.Rect(25, 25, 50, 50)
        assert physics.overlap(a, b) is True

    def test_overlap_false(self):
        """Two non-overlapping rects → False."""
        a = pygame.Rect(0, 0, 50, 50)
        b = pygame.Rect(100, 100, 50, 50)
        assert physics.overlap(a, b) is False

    def test_overlap_touching_edges(self):
        """Rects that only share an edge (adjacent) → False (not overlapping)."""
        a = pygame.Rect(0, 0, 50, 50)
        b = pygame.Rect(50, 0, 50, 50)
        # pygame.Rect.colliderect is False for edge-touching only
        assert physics.overlap(a, b) is False

    def test_overlap_contained(self):
        """One rect fully inside the other → True."""
        a = pygame.Rect(10, 10, 100, 100)
        b = pygame.Rect(20, 20, 20, 20)
        assert physics.overlap(a, b) is True


# ---------------------------------------------------------------------------
# check_hazards
# ---------------------------------------------------------------------------

class TestCheckHazards:
    def test_check_hazards_hit(self):
        """Entity centre overlapping a hazard → True."""
        entity = pygame.Rect(100, 100, 32, 48)
        hazard = pygame.Rect(100, 100, 32, 48)
        assert physics.check_hazards(entity, [hazard]) is True

    def test_check_hazards_miss(self):
        """Entity far from hazard → False."""
        entity = pygame.Rect(0, 0, 32, 48)
        hazard = pygame.Rect(500, 500, 48, 48)
        assert physics.check_hazards(entity, [hazard]) is False

    def test_check_hazards_empty_list(self):
        """No hazards → False."""
        entity = pygame.Rect(0, 0, 32, 48)
        assert physics.check_hazards(entity, []) is False

    def test_check_hazards_grazing_edge_no_hit(self):
        """Entity just grazing a hazard edge (inset avoids false positive) → False."""
        # Entity right edge just touching hazard left edge — inset means no collision
        entity = pygame.Rect(0, 100, 32, 48)
        hazard = pygame.Rect(31, 100, 48, 48)   # just at the edge
        # The inset deflates by 4 (2 each side), so entity inset right = 30; hazard at 31 → no overlap
        assert physics.check_hazards(entity, [hazard]) is False


# ---------------------------------------------------------------------------
# check_checkpoints
# ---------------------------------------------------------------------------

class TestCheckCheckpoints:
    def test_check_checkpoints_hit_first(self):
        """Overlapping the first checkpoint returns index 0."""
        entity = pygame.Rect(100, 100, 32, 48)
        cp0 = pygame.Rect(100, 100, 48, 48)
        cp1 = pygame.Rect(300, 300, 48, 48)
        result = physics.check_checkpoints(entity, [cp0, cp1])
        assert result == 0

    def test_check_checkpoints_hit_second(self):
        """Overlapping only the second checkpoint returns index 1."""
        entity = pygame.Rect(300, 300, 32, 48)
        cp0 = pygame.Rect(100, 100, 48, 48)
        cp1 = pygame.Rect(300, 300, 48, 48)
        result = physics.check_checkpoints(entity, [cp0, cp1])
        assert result == 1

    def test_check_checkpoints_no_hit(self):
        """Entity not overlapping any checkpoint → None."""
        entity = pygame.Rect(0, 0, 32, 48)
        cp0 = pygame.Rect(500, 500, 48, 48)
        result = physics.check_checkpoints(entity, [cp0])
        assert result is None

    def test_check_checkpoints_empty(self):
        """Empty checkpoint list → None."""
        entity = pygame.Rect(0, 0, 32, 48)
        assert physics.check_checkpoints(entity, []) is None


# ---------------------------------------------------------------------------
# check_goal
# ---------------------------------------------------------------------------

class TestCheckGoal:
    def test_check_goal_overlapping(self):
        """Entity overlapping goal rect → True."""
        entity = pygame.Rect(200, 200, 32, 48)
        goal = pygame.Rect(200, 200, 48, 48)
        assert physics.check_goal(entity, goal) is True

    def test_check_goal_not_overlapping(self):
        """Entity far from goal → False."""
        entity = pygame.Rect(0, 0, 32, 48)
        goal = pygame.Rect(500, 500, 48, 48)
        assert physics.check_goal(entity, goal) is False
