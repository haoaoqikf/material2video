"""折叠示例的生成器必须保留讲解依赖的几何关系。"""

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "styles/vibe-night/examples/fold/tools/gen_layout.py"
SPEC = importlib.util.spec_from_file_location("fold_layout_generator", SCRIPT)
assert SPEC and SPEC.loader
layout_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout_generator)


def test_generated_layout_is_repeatable_and_preserves_connections():
    layout = layout_generator.build_layout(2)
    assert layout == layout_generator.build_layout(2)
    cells = [tuple(cell) for cell in layout["cells"]]
    assert len(cells) == len(set(cells)) == 146
    assert cells[5] == tuple(layout["knobCell"])
    assert all((b[0] - a[0], b[1] - a[1]) in layout_generator.NEIGHBORS
               for a, b in zip(cells, cells[1:]))
    assert layout["pitch"] < 2 * layout["R"]
    assert not {(x + 12, y) for x, y in cells}.intersection(cells)


def test_invalid_seed_keeps_existing_output(tmp_path):
    output = tmp_path / "layout.json"
    original = json.dumps({"sentinel": True})
    output.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="seed"):
        layout_generator.main(["--seed", "0", "--out", str(output)])
    assert output.read_text(encoding="utf-8") == original


def test_committed_layout_matches_generator():
    path = SCRIPT.parents[1] / "scenes/layout.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert layout_generator.build_layout(committed["seed"]) == committed
