"""
physics.py — Axis-separated rectangle collision resolution for "Just One More Try".

Player (and entity) positions are stored as (float, float) pixel coordinates by the
caller. pygame.Rect is constructed only for spatial queries and is never stored
persistently here. All functions are *pure* from the caller's perspective: they
return new values and never mutate their inputs. Callers are responsible for
writing the returned values back into their own state.
"""

import pygame
from settings import GRAVITY, MAX_FALL_SPEED, FIXED_DT


# ---------------------------------------------------------------------------
# Gravity
# ---------------------------------------------------------------------------

def apply_gravity(vy: float, dt: float = FIXED_DT) -> float:
    """Apply gravity to vertical velocity, capped at MAX_FALL_SPEED.

    Args:
        vy:  Current vertical velocity (px/s, positive = downward).
        dt:  Time step in seconds.

    Returns:
        New vertical velocity after gravity is applied.
    """
    return min(vy + GRAVITY * dt, MAX_FALL_SPEED)


# ---------------------------------------------------------------------------
# Horizontal collision resolution
# ---------------------------------------------------------------------------

def resolve_x(
    entity_rect: pygame.Rect,
    tiles: list,
    velocity_x: float,
    dt: float = FIXED_DT,
) -> tuple[pygame.Rect, float, bool]:
    """Move entity horizontally and push it out of any solid tiles.

    Args:
        entity_rect: Current bounding rect of the entity (not modified).
        tiles:       List of pygame.Rect objects representing solid tiles.
        velocity_x:  Horizontal velocity (px/s, positive = right).
        dt:          Time step in seconds.

    Returns:
        (new_rect, new_vx, hit_wall)
        new_rect  — updated rect after movement and push-out.
        new_vx    — 0 if a wall was hit, otherwise unchanged velocity_x.
        hit_wall  — True if at least one horizontal collision occurred.
    """
    new_rect = entity_rect.copy()
    new_rect.x += int(velocity_x * dt)

    hit_wall = False
    for tile in tiles:
        if new_rect.colliderect(tile):
            hit_wall = True
            if velocity_x > 0:
                # Moving right → push left so right edge aligns with tile left
                new_rect.right = tile.left
            elif velocity_x < 0:
                # Moving left → push right so left edge aligns with tile right
                new_rect.left = tile.right
            velocity_x = 0

    return new_rect, velocity_x, hit_wall


# ---------------------------------------------------------------------------
# Vertical collision resolution
# ---------------------------------------------------------------------------

def resolve_y(
    entity_rect: pygame.Rect,
    tiles: list,
    velocity_y: float,
    dt: float = FIXED_DT,
) -> tuple[pygame.Rect, float, bool]:
    """Move entity vertically and push it out of any solid tiles.

    Gravity is intentionally NOT applied here; the Player applies gravity
    before calling this function so that troll hooks can intercept it.

    Args:
        entity_rect: Current bounding rect of the entity (not modified).
        tiles:       List of pygame.Rect objects representing solid tiles.
        velocity_y:  Vertical velocity (px/s, positive = downward).
        dt:          Time step in seconds.

    Returns:
        (new_rect, new_vy, on_ground)
        new_rect  — updated rect after movement and push-out.
        new_vy    — 0 if a floor/ceiling was hit, otherwise unchanged velocity_y.
        on_ground — True if the entity landed on top of a tile this step.
    """
    new_rect = entity_rect.copy()
    new_rect.y += int(velocity_y * dt)

    on_ground = False
    for tile in tiles:
        if new_rect.colliderect(tile):
            if velocity_y > 0:
                # Falling down → land on tile top
                new_rect.bottom = tile.top
                on_ground = True
            elif velocity_y < 0:
                # Moving up → hit ceiling, snap bottom of entity to tile bottom
                new_rect.top = tile.bottom
            velocity_y = 0

    return new_rect, velocity_y, on_ground


# ---------------------------------------------------------------------------
# Generic overlap test
# ---------------------------------------------------------------------------

def overlap(rect_a: pygame.Rect, rect_b: pygame.Rect) -> bool:
    """Return True if rect_a and rect_b overlap.

    Args:
        rect_a: First rectangle.
        rect_b: Second rectangle.

    Returns:
        True if the rectangles intersect.
    """
    return rect_a.colliderect(rect_b)


# ---------------------------------------------------------------------------
# Hazard detection
# ---------------------------------------------------------------------------

def check_hazards(entity_rect: pygame.Rect, hazard_rects: list) -> bool:
    """Return True if the entity overlaps any hazard.

    Uses a 2-pixel inset on all sides of the entity rect to avoid false
    positives when the entity is merely grazing an edge.

    Args:
        entity_rect:  Bounding rect of the entity.
        hazard_rects: List of pygame.Rect objects for hazard zones.

    Returns:
        True if the inset entity rect overlaps at least one hazard.
    """
    inset = entity_rect.inflate(-4, -4)  # 2 px inset on each side
    for hazard in hazard_rects:
        if inset.colliderect(hazard):
            return True
    return False


# ---------------------------------------------------------------------------
# Checkpoint detection
# ---------------------------------------------------------------------------

def check_checkpoints(
    entity_rect: pygame.Rect, checkpoint_rects: list
) -> int | None:
    """Return the index of the first checkpoint the entity overlaps, or None.

    Args:
        entity_rect:      Bounding rect of the entity.
        checkpoint_rects: Ordered list of pygame.Rect checkpoint zones.

    Returns:
        Integer index of the first overlapping checkpoint, or None.
    """
    for i, cp in enumerate(checkpoint_rects):
        if entity_rect.colliderect(cp):
            return i
    return None


# ---------------------------------------------------------------------------
# Goal detection
# ---------------------------------------------------------------------------

def check_goal(entity_rect: pygame.Rect, goal_rect: pygame.Rect) -> bool:
    """Return True if the entity has reached the goal.

    Args:
        entity_rect: Bounding rect of the entity.
        goal_rect:   Bounding rect of the goal zone.

    Returns:
        True if the rectangles intersect.
    """
    return entity_rect.colliderect(goal_rect)


# ---------------------------------------------------------------------------
# Slippery-edge proximity check
# ---------------------------------------------------------------------------

def near_slippery_edge(
    entity_rect: pygame.Rect,
    slippery_rects: list,
    threshold: int = 8,
) -> bool:
    """Return True if the entity is near the left or right edge of a slippery tile.

    "Near" means the entity's bottom edge is within *threshold* pixels above the
    tile's top surface AND the entity's horizontal centre is within *threshold*
    pixels of the tile's left or right edge. This is used by the Player to decide
    whether to apply extra slippery friction.

    Args:
        entity_rect:    Bounding rect of the entity.
        slippery_rects: List of pygame.Rect objects for slippery tiles.
        threshold:      Pixel proximity threshold (default 8).

    Returns:
        True if the entity is near a slippery tile edge.
    """
    for tile in slippery_rects:
        # Entity bottom must be close to tile top (i.e., standing on or just above it)
        if abs(entity_rect.bottom - tile.top) <= threshold:
            # Check horizontal proximity to left or right edge of tile
            if (abs(entity_rect.centerx - tile.left) <= threshold or
                    abs(entity_rect.centerx - tile.right) <= threshold):
                return True
    return False
