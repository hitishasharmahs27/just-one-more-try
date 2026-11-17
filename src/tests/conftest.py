"""
conftest.py — Shared fixtures for "Just One More Try" test suite.

Must set SDL env vars before any pygame import.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys
import pathlib

import pygame
import pytest

# ---------------------------------------------------------------------------
# Ensure the src/ directory is on sys.path so tests can import game modules.
# ---------------------------------------------------------------------------
SRC_DIR = pathlib.Path(__file__).parent.parent  # …/src/
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

LEVELS_DIR = SRC_DIR / 'levels'


@pytest.fixture(scope='session', autouse=True)
def pygame_init():
    """Initialise pygame once for the whole test session (headless)."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def levels_dir() -> pathlib.Path:
    """Return the path to the levels/ directory."""
    return LEVELS_DIR


def level_path(n: int) -> str:
    """Absolute path string for levels/levelN.txt."""
    return str(LEVELS_DIR / f'level{n}.txt')
