"""折叠示例的布局关系：先验证几何，再谈画面。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "styles" / "examples" / "vibe-night" / "fold"
LAYOUT = EXAMPLE / "scenes" / "layout.json"
GENERATOR = EXAMPLE / "tools" / "gen_layout.py"
NEIGHBORS = {(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)}


def load_layout() -> dict:
    return json.loads(LAYOUT.read_text(encoding="utf-8"))


def test_layout_has_146_adjacent_unique_cells():
    layout = load_layout()
    cells = [tuple(cell) for cell in layout["cells"]]
    assert len(cells) == 146
    assert len(set(cells)) == 146
    for current, following in zip(cells, cells[1:]):
        delta = (following[0] - current[0], following[1] - current[1])
        assert delta in NEIGHBORS, f"第 {cells.index(current)} 与下一颗不相邻：{current} → {following}"


def test_layout_declares_knob_notch_and_cavity():
    layout = load_layout()
    cells = {tuple(cell) for cell in layout["cells"]}
    assert layout["knob"] == 5
    assert tuple(layout["cells"][layout["knob"]]) == tuple(layout["knobCell"])
    assert tuple(layout["knobCell"]) in cells
    assert tuple(layout["notchCell"]) not in cells
    assert all(tuple(cell) not in cells for cell in layout["cavityCells"])
    assert len(layout["cavityCells"]) == 2


def test_docking_translation_does_not_overlap_and_actually_contacts():
    layout = load_layout()
    cells = {tuple(cell) for cell in layout["cells"]}
    dx, dy = layout["grid"]["dockCells"]
    shifted = {(i + dx, j + dy) for i, j in cells}
    assert not cells & shifted, "相邻两团的格点不能重合"
    # 前一团的凸点应当落在后一团的凹口位置；两者中心距小于 2R，才会交错。
    knob = tuple(layout["knobCell"])
    notch = tuple(layout["notchCell"])
    assert (notch[0] + dx, notch[1] + dy) == knob
    assert layout["pitch"] < 2 * layout["R"]


def test_points_match_cells_and_use_the_declared_pitch():
    layout = load_layout()
    d = layout["D"]
    for (x, y), (i, j) in zip(layout["pts"], layout["cells"]):
        assert x == round(d * (i + j / 2), 2)
        assert y == round(d * (3 ** 0.5 / 2) * j, 2)
    assert layout["pitch"] == round(layout["grid"]["dockCells"][0] * d, 2)


def test_committed_layout_is_reproducible(tmp_path):
    out = tmp_path / "layout.json"
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text(encoding="utf-8")) == load_layout()


def test_scene_consumes_generated_layout_instead_of_ring_spiral():
    source = (EXAMPLE / "scenes" / "fold.tsx").read_text(encoding="utf-8")
    assert "from './layout.json'" in source
    assert "const PITCH = F.pitch" in source
    assert "const pocket: Vec = F.cavity" in source
    assert "BLOB_RADIUS * 2 + 6" not in source
    assert "const RING = 7" not in source
