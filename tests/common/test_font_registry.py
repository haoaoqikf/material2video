"""字体仓：登记、摘要、许可与离线校验。"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "fonts"
REGISTRY = FONTS / "registry.json"


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_entries_are_complete():
    data = registry()
    assert data["schemaVersion"] == 1
    entries = data["fonts"]
    assert {"lat-inter", "sans-cn", "serif-cn-subset"} <= {entry["id"] for entry in entries}
    assert len({entry['id'] for entry in entries}) == len(entries)
    for entry in entries:
        assert entry["bytes"] > 0
        assert len(entry["sha256"]) == 64
        assert (FONTS / entry["license"]).is_file(), f"缺少许可：{entry['license']}"
        assert entry["targets"], f"{entry['id']} 没有恢复目标"
        for target in entry["targets"]:
            assert not Path(target).is_absolute()


def test_registered_files_match_digests():
    for entry in registry()["fonts"]:
        path = FONTS / "files" / entry["file"]
        if not path.is_file():
            pytest.skip("字体未恢复；先运行 uv run python fonts/fetch.py")
        assert path.stat().st_size == entry["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_check_reports_ready():
    if not (FONTS / "files").is_dir() or not any((FONTS / "files").iterdir()):
        pytest.skip("字体未恢复；先运行 uv run python fonts/fetch.py")
    result = subprocess.run([sys.executable, str(FONTS / "fetch.py"), "--check"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "字体就绪" in result.stdout


def test_check_fails_when_files_missing(tmp_path):
    """复制一份字体仓到临时目录，缺失时必须返回非零并给出恢复命令。"""
    root = tmp_path / "fonts"
    root.mkdir()
    shutil.copy(FONTS / "fetch.py", root / "fetch.py")
    (root / "licenses").mkdir()
    (root / "licenses" / "lic.txt").write_text("license", encoding="utf-8")
    entry = {"id": "missing", "file": "missing.ttf", "source": "test", "version": "1",
             "bytes": 1, "sha256": "0" * 64, "license": "licenses/lic.txt", "targets": []}
    (root / "registry.json").write_text(
        json.dumps({"schemaVersion": 1, "fonts": [entry]}, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([sys.executable, str(root / "fetch.py"), "--check"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode != 0
    assert "缺少" in result.stdout
    assert "fonts/fetch.py" in result.stdout


def test_font_files_reports_restore_hint(tmp_path):
    from m2v.core.errors import M2VError
    from m2v.engine import contract_page

    (tmp_path / "web/src/assets").mkdir(parents=True)
    (tmp_path / "web/src/assets/fonts.json").write_text(json.dumps({
        "sourceDirFromWeb": "../fonts/files",
        "files": [{"family": "X", "file": "missing.ttf", "weight": "400",
                   "usage": "test", "license": "L.txt"}],
    }), encoding="utf-8")
    with pytest.raises(M2VError, match="fonts/fetch.py"):
        contract_page.font_files(tmp_path)
