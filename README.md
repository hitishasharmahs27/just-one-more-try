# Just One More Try
A troll 2D platformer — unfair by design, never broken by accident.

## 🚀 Quick Start & Setup

### Option 1: macOS One-Click
Simply double-click:
```text
run_mac.command
```

### Option 2: Windows One-Click (Build / Run .exe)
Simply double-click:
```text
build_windows_exe.bat
```

### Option 3: Command Line (macOS / Linux / Windows)
Clone or open the repository folder, then run:

```bash
# 1. Install dependencies (works from repository root)
pip install -r requirements.txt

# 2. Run the game
python3 src/main.py
```
*(On Windows cmd/powershell, replace `python3` with `python`).*

---

## 🎮 Controls
| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move left / right |
| Space / W / Up | Jump |
| R | Restart level |
| F1 | Toggle debug (view troll parameters & hitboxes) |
| Escape | Return to menu / Quit |

---

## 🗺️ Levels & Progressive Difficulty
5 levels, each introducing one new troll mechanic:
1. **Level 1**: Variable jump height
2. **Level 2**: + Input buffer delay on jumps
3. **Level 3**: + Unreliable checkpoints (probabilistic save failure)
4. **Level 4**: + Slippery edges (reduced platform edge friction)
5. **Level 5**: + Vanishing & invisible platforms

---

## 🧪 Running Automated Tests
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest src/tests/ -v
```

---

## 📂 Architecture Overview
| File | Role |
|------|------|
| `src/main.py` | Application entry point |
| `src/settings.py` | All tunable constants & difficulty matrices |
| `src/game.py` | 60 FPS fixed-timestep loop & state machine |
| `src/player.py` | Shinchan player controller & hook integration |
| `src/physics.py` | Axis-separated AABB collision & gravity |
| `src/level.py` | Level loading & ASCII tile grid parser |
| `src/troll.py` | Decoupled Troll Mechanics Engine |
| `src/ui.py` | HUD, menus, and snarky death message overlays |
