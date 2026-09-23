#!/usr/bin/env python3
"""
Conway's Game of Life that lives in a GitHub profile README.

Renders an *animated* SVG: each run evolves the world MOVIE_FRAMES generations
and bakes them into a looping SMIL movie, so the profile shows the simulation
actually playing, not a static snapshot.

Stdlib only. Usage:
    python scripts/life.py step                 # evolve a full episode, re-render
    python scripts/life.py toggle 12,5 13,5     # toggle cells, then evolve an episode
    python scripts/life.py render               # re-render movie from current state

State lives in state/life.json, output in dist/life.svg.
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "state" / "life.json"
SVG_FILE = ROOT / "dist" / "life.svg"

COLS, ROWS = 72, 24
CELL, GAP = 11, 1          # cell size px, gap px
PITCH = CELL + GAP
PAD = 8                    # svg padding px
MIN_POP_BEFORE_GLIDER = 6  # inject a glider if population drops below this

MOVIE_FRAMES = 30          # generations per episode
FRAME_SECONDS = 0.5        # seconds per frame
DURATION = MOVIE_FRAMES * FRAME_SECONDS
HOLD = 1.0 / MOVIE_FRAMES  # fraction of loop each frame is visible

BG = "#0d1117"
GRID = "#161b22"
GEN_COLOR = "#8b949e"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"generation": 0, "cells": [], "ages": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def cell_set(state):
    return {tuple(c) for c in state["cells"]}


def seed(state):
    """Random soup + a couple of gliders for a lively start."""
    rng = random.Random()
    cells = set()
    for _ in range(int(COLS * ROWS * 0.12)):
        cells.add((rng.randrange(COLS), rng.randrange(ROWS)))
    for gx, gy in [(4, 4), (COLS - 12, 6)]:
        cells |= {(gx + 1, gy), (gx + 2, gy + 1), (gx, gy + 2), (gx + 1, gy + 2), (gx + 2, gy + 2)}
    state["cells"] = [list(c) for c in cells]
    state["ages"] = {f"{x},{y}": 1 for x, y in cells}
    state["generation"] = 0


def step_once(state):
    live = cell_set(state)
    ages = state.get("ages", {})
    counts = {}
    for x, y in live:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    nx, ny = (x + dx) % COLS, (y + dy) % ROWS
                    counts[(nx, ny)] = counts.get((nx, ny), 0) + 1
    new_live, new_ages = set(), {}
    for (x, y), n in counts.items():
        if n == 3 or (n == 2 and (x, y) in live):
            new_live.add((x, y))
            new_ages[f"{x},{y}"] = ages.get(f"{x},{y}", 0) + 1
    state["cells"] = [list(c) for c in new_live]
    state["ages"] = new_ages
    state["generation"] = state.get("generation", 0) + 1
    if len(new_live) < MIN_POP_BEFORE_GLIDER:
        inject_glider(state)


def inject_glider(state):
    rng = random.Random(state["generation"])
    gx, gy = rng.randrange(2, COLS - 4), rng.randrange(2, ROWS - 4)
    live = cell_set(state)
    glider = {(gx + 1, gy), (gx + 2, gy + 1), (gx, gy + 2), (gx + 1, gy + 2), (gx + 2, gy + 2)}
    live |= glider
    for x, y in glider:
        state["ages"][f"{x},{y}"] = 1
    state["cells"] = [list(c) for c in live]


def toggle(state, coords):
    live = cell_set(state)
    for x, y in coords:
        x, y = x % COLS, y % ROWS
        if (x, y) in live:
            live.discard((x, y))
            state["ages"].pop(f"{x},{y}", None)
        else:
            live.add((x, y))
            state["ages"][f"{x},{y}"] = 1
    state["cells"] = [list(c) for c in live]



def cell_color(age):
    """Young cells glow bright green; ancient ones fade to deep teal."""
    if age <= 1:
        return "#7ee787"
    if age <= 3:
        return "#3fb950"
    if age <= 8:
        return "#2ea043"
    return "#1a7f6e"


def snapshot(state):
    """(live cells, per-cell ages) for one frame."""
    return cell_set(state), dict(state.get("ages", {}))


def render_movie(frames, generation, population):
    w = PAD * 2 + COLS * PITCH
    h = PAD * 2 + ROWS * PITCH + 22

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" rx="8" fill="{BG}"/>',
        # empty grid drawn once via a pattern (keeps file small)
        f'<defs><pattern id="g" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse">'
        f'<rect width="{CELL}" height="{CELL}" rx="2" fill="{GRID}"/></pattern></defs>',
        f'<rect x="{PAD}" y="{PAD}" width="{COLS * PITCH}" height="{ROWS * PITCH}" fill="url(#g)"/>',
    ]
    for i, (live, ages) in enumerate(frames):
        begin = -i * FRAME_SECONDS
        # fade in fast, hold, fade out, stay hidden for the rest of the loop
        parts.append(
            f'<g opacity="0"><animate attributeName="opacity" '
            f'values="0;1;1;0;0" keyTimes="0;0.002;{HOLD - 0.004:.4f};{HOLD:.4f};1" '
            f'dur="{DURATION}s" begin="{begin}s" repeatCount="indefinite"/>'
        )
        for gx, gy in sorted(live):
            x = PAD + gx * PITCH
            y = PAD + gy * PITCH
            age = ages.get(f"{gx},{gy}", 1)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{cell_color(age)}"/>'
            )
        parts.append("</g>")
    parts.append(
        f'<text x="{PAD}" y="{h - 8}" font-family="monospace" font-size="12" '
        f'fill="{GEN_COLOR}">generation {generation} Â· population {population} Â· '
        f'open an issue titled "life: x,y" to play</text>'
    )
    parts.append("</svg>")
    SVG_FILE.parent.mkdir(parents=True, exist_ok=True)
    SVG_FILE.write_text("\n".join(parts), encoding="utf-8")


def evolve_episode(state):
    """Advance MOVIE_FRAMES generations, collecting every frame for the movie."""
    frames = [snapshot(state)]
    for _ in range(MOVIE_FRAMES):
        step_once(state)
        frames.append(snapshot(state))
    render_movie(frames, state["generation"], len(state["cells"]))


def main():
    state = load_state()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "step"

    if not state["cells"]:
        seed(state)

    if cmd == "step":
        evolve_episode(state)
    elif cmd == "toggle":
        coords = []
        for arg in sys.argv[2:]:
            x, y = arg.split(",")
            coords.append((int(x), int(y)))
        toggle(state, coords)
        evolve_episode(state)
    elif cmd == "render":
        evolve_episode(state)
    else:
        sys.exit(f"unknown command: {cmd}")

    save_state(state)
    print(f"gen={state['generation']} population={len(state['cells'])}")


if __name__ == "__main__":
    main()
