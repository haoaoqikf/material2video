# -*- coding: utf-8 -*-
"""生成折叠示例的六角格布局，并在写盘前检查关系是否成立。

布局不是「画得像一团」，而是先满足讲解需要：

- 146 颗珠子，路径走遍每个格点，相邻两颗的格距始终为 `D`；
- 第 6 颗（索引 5）落在右侧凸点（knob）上，成为表面的黏点；
- 左侧留一个凹口（notch），相邻一团平移 `pitch` 后，凸点正好卡进凹口，
  两团的格点集合不相交；
- 中间留两个相邻空腔（cavity），作为氧分子落点。

运行：

    python examples/text-motion/fold/tools/gen_layout.py

输出 `scenes/layout.json`。脚本会先断言关系，再写文件；不满足时直接失败，
不会用一张「看起来差不多」的图掩盖几何问题。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

D = 31.5
SQ3 = math.sqrt(3) / 2
NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
KNOB_CELL = (6, 0)
NOTCH_CELL = (-6, 0)
CAVITY_CELLS = [(-2, 1), (-1, 1)]
#: 两团接合时的格点平移；12 格 = 中心距 pitch。
DOCK = (12, 0)
GRID_RADIUS_SQUARED = 39
TOTAL = 146


def cell_xy(cell: tuple[int, int]) -> tuple[float, float]:
    return D * (cell[0] + cell[1] / 2), D * SQ3 * cell[1]


def build_cells() -> set[tuple[int, int]]:
    cells = {(i, j) for i in range(-9, 10) for j in range(-9, 10)
             if i * i + i * j + j * j <= GRID_RADIUS_SQUARED}
    assert len(cells) == 151, len(cells)
    # 右侧只留 knob 一个点鼓出来；左侧留 notch；中间留两个相邻空腔。
    cells -= {(5, 2), (7, -2)}
    cells -= {NOTCH_CELL}
    cells -= set(CAVITY_CELLS)
    assert len(cells) == TOTAL, len(cells)
    assert KNOB_CELL in cells
    assert NOTCH_CELL not in cells
    assert not any(cell in cells for cell in CAVITY_CELLS)
    # 相邻一团平移 DOCK 后不能有格点重合；凸点会落进凹口，而不是撞上珠子。
    assert not any((i + DOCK[0], j + DOCK[1]) in cells for (i, j) in cells), "相邻两团会相撞"
    return cells


def connected(cells: set[tuple[int, int]], adjacency: dict, free: set[tuple[int, int]],
              start: tuple[int, int]) -> bool:
    seen, stack = {start}, [start]
    while stack:
        node = stack.pop()
        for neighbor in adjacency[node]:
            if neighbor in free and neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == len(free)


def find_path(cells: set[tuple[int, int]], seed: int, limit: int = 2_000_000) -> list[tuple[int, int]] | None:
    """找一条从外围绕到 knob、再走遍其余格点的哈密顿路径。

    前 6 个点固定为「走到 knob」，因此索引 5 就是第 6 颗珠子；其余部分用
    Warnsdorff 顺序（先走出路少的格点）加连通性剪枝搜索。
    """
    adjacency = {cell: [(cell[0] + di, cell[1] + dj) for di, dj in NEIGHBORS
                        if (cell[0] + di, cell[1] + dj) in cells] for cell in cells}
    rnd = random.Random(seed)
    a, b = rnd.sample(adjacency[KNOB_CELL], 2)
    prefix = [a]
    used = {KNOB_CELL, a, b}
    while len(prefix) < 5:
        candidates = [neighbor for neighbor in adjacency[prefix[-1]] if neighbor not in used]
        if not candidates:
            return None
        candidates.sort(key=lambda cell: (len(adjacency[cell]), rnd.random()))
        prefix.append(candidates[0])
        used.add(candidates[0])
    path = prefix[::-1] + [KNOB_CELL, b]
    free = set(cells) - set(path)
    if not connected(cells, adjacency, free | {b}, b):
        return None
    steps = 0
    sys.setrecursionlimit(10000)

    def search(current: tuple[int, int]) -> bool:
        nonlocal steps
        if not free:
            return True
        steps += 1
        if steps > limit:
            return False
        candidates = [neighbor for neighbor in adjacency[current] if neighbor in free]
        candidates.sort(key=lambda cell: (sum(1 for q in adjacency[cell] if q in free), rnd.random()))
        for neighbor in candidates:
            free.discard(neighbor)
            path.append(neighbor)
            # 剪枝：剩下的格点里不能有走不到的死角（最多允许一个终点）。
            dead = sum(1 for q in free if not any(r in free or r == neighbor for r in adjacency[q]))
            if dead <= 0 and (len(free) < 2 or len(free) % 6
                              or connected(cells, adjacency, free, next(iter(free)))):
                if search(neighbor):
                    return True
            path.pop()
            free.add(neighbor)
        return False

    return path if search(b) else None


def build_layout(seed: int = 1) -> dict:
    if not 1 <= seed <= 100_000:
        raise ValueError("seed 必须在 1–100000 之间")
    cells = build_cells()
    path = None
    for candidate in range(seed, seed + 400):
        path = find_path(cells, candidate)
        if path:
            seed = candidate
            break
    if path is None:
        raise SystemExit("没有找到满足关系的路径；检查格点集合或空腔位置")

    assert len(path) == TOTAL and len(set(path)) == TOTAL
    assert path[5] == KNOB_CELL
    assert all(path[index + 1] in {
        (path[index][0] + di, path[index][1] + dj) for di, dj in NEIGHBORS
    } for index in range(TOTAL - 1))

    points = [cell_xy(cell) for cell in path]
    radius = max(math.hypot(*cell_xy(cell)) for cell in cells)
    pitch = DOCK[0] * D
    # 接合必须真的接触：包围圆可以重叠，但格点不能重合；pitch 小于 2R。
    assert pitch < 2 * radius, (pitch, radius)
    assert not any((i + DOCK[0], j + DOCK[1]) in cells for (i, j) in cells)

    cavity = [sum(cell_xy(cell)[axis] for cell in CAVITY_CELLS) / len(CAVITY_CELLS)
              for axis in (0, 1)]
    notch = cell_xy(NOTCH_CELL)
    return {
        "generator": "fold-layout-v1",
        "seed": seed,
        "D": D,
        "grid": {"radiusSquared": GRID_RADIUS_SQUARED, "dockCells": list(DOCK)},
        "pitch": round(pitch, 2),
        "R": round(radius, 2),
        "knob": 5,
        "knobCell": list(KNOB_CELL),
        "notchCell": list(NOTCH_CELL),
        "cavityCells": [list(cell) for cell in CAVITY_CELLS],
        "cavity": [round(value, 2) for value in cavity],
        "notch": [round(value, 2) for value in notch],
        "cells": [list(cell) for cell in path],
        "pts": [[round(value, 2) for value in point] for point in points],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成并校验折叠示例的六角格布局")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parents[1] / "scenes" / "layout.json")
    args = parser.parse_args(argv)
    layout = build_layout(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"layout: {args.out}  seed={layout['seed']}  R={layout['R']}  pitch={layout['pitch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
