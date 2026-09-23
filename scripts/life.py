#!/usr/bin/env python3
"""
Conway's Game of Life that lives in a GitHub profile README.

Stdlib only. Usage:
    python scripts/life.py step                 # advance one generation, re-render
    python scripts/life.py toggle 12,5 13,5     # toggle cells (used by issue workflow)
    python scripts/life.py render               # just re-render the SVG

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
PAD = 8                    # svg padding px
MIN_POP_BEFORE_GLIDER = 6  # inject a glider if population drops below this

BG = "#0d1117"
GRID = "#161b22"
GEN_COLOR = "#8b949e"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"generation": 0, "cells": [], "ages": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1))


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


def step(state):
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


def render(state):
    live = cell_set(state)
    ages = state.get("ages", {})
    gen = state.get("generation", 0)
    w = PAD * 2 + COLS * (CELL + GAP)
    h = PAD * 2 + ROWS * (CELL + GAP) + 22

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" rx="8" fill="{BG}"/>',
    ]
    for gy in range(ROWS):
        for gx in range(COLS):
            x = PAD + gx * (CELL + GAP)
            y = PAD + gy * (CELL + GAP)
            if (gx, gy) in live:
                age = ages.get(f"{gx},{gy}", 1)
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                    f'fill="{cell_color(age)}"><title>age {age}</title></rect>'
                )
            else:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{GRID}"/>'
                )
    parts.append(
        f'<text x="{PAD}" y="{h - 8}" font-family="monospace" font-size="12" '
        f'fill="{GEN_COLOR}">generation {gen} · population {len(live)} · '
        f'open an issue titled "life: x,y" to play</text>'
    )
    parts.append("</svg>")
    SVG_FILE.parent.mkdir(parents=True, exist_ok=True)
    SVG_FILE.write_text("\n".join(parts))


def main():
    state = load_state()
    if not state["cells"] and (len(sys.argv) < 2 or sys.argv[1] != "toggle"):
        seed(state)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "step"
    if cmd == "step":
        if not state["cells"]:
            seed(state)
        step(state)
    elif cmd == "toggle":
        coords = []
        for arg in sys.argv[2:]:
            x, y = arg.split(",")
            coords.append((int(x), int(y)))
        toggle(state, coords)
    elif cmd == "render":
        if not state["cells"]:
            seed(state)
    else:
        sys.exit(f"unknown command: {cmd}")

    save_state(state)
    render(state)
    print(f"gen={state['generation']} population={len(state['cells'])}")


if __name__ == "__main__":
    main()
