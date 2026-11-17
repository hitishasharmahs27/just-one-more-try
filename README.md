# Just One More Try
A troll 2D platformer — unfair by design, never broken by accident.

## Setup
```bash
pip install -r src/requirements.txt
cd src && python main.py
```

## Controls
| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| Space / W / Up | Jump |
| R | Restart level |
| F1 | Toggle debug (troll info) |
| Escape | Quit |

## Levels
5 levels, each adding one new troll mechanic:
1. Variable jump height
2. + Input delay
3. + Unreliable checkpoints
4. + Slippery edges
5. + Vanishing & invisible platforms

## Running tests
```bash
cd src && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/ -v
```

## Modules
| File | Role |
|------|------|
| main.py | Entry point |
| settings.py | All constants |
| game.py | Game Manager & loop |
| player.py | Player Controller |
| physics.py | Collision & Physics |
| level.py | Level Manager |
| troll.py | Troll Mechanics Engine |
| ui.py | UI Module |
