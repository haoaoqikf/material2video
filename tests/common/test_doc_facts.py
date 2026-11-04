"""文档结构契约：链接可达、主规格有效、入口与能力目录一致。"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from guidance_docs import anchors


ROOT = Path(__file__).resolve().parents[2]


def tracked_markdown() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "*.md"], cwd=ROOT, text=True, encoding="utf-8"
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("需要 git 才能检查纳入版本管理的文档")
    files = [ROOT / line for line in output.splitlines() if line]
    return [
        path for path in files
        if path.exists() and "openspec/changes/archive/" not in path.as_posix()
    ]


def test_tracked_markdown_links_and_anchors_resolve() -> None:
    files = tracked_markdown()
    anchor_cache = {path: anchors(path.read_text(encoding='utf-8')) for path in files}
    missing: list[str] = []
    for path in files:
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for match in re.finditer(r"\[[^\]]*\]\(([^)\s]+)\)", text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            relative, _, fragment = target.partition("#")
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target}（文件不存在）")
                continue
            if fragment and resolved.suffix == ".md":
                if resolved in anchor_cache and fragment not in anchor_cache[resolved]:
                    missing.append(f"{path.relative_to(ROOT)} -> {target}（锚点不存在）")
    assert not missing, "\n".join(missing)


def test_open_specs_are_retired_only_through_archive() -> None:
    specs = sorted((ROOT / "openspec/specs").glob("*/spec.md"))
    assert specs, "至少应有一个现行主规格"
    empty = [path.relative_to(ROOT).as_posix() for path in specs if "## Purpose" not in path.read_text(encoding="utf-8")]
    assert not empty, f"主规格缺少 Purpose: {empty}"


def test_config_type_list_matches_catalog() -> None:
    catalog = json.loads((ROOT / "src/m2v/type_system/catalog.json").read_text(encoding="utf-8"))
    names = {row["name"] for row in catalog["types"]}
    config = (ROOT / "openspec/config.yaml").read_text(encoding="utf-8")
    missing = sorted(name for name in names if name not in config)
    assert not missing, f"openspec/config.yaml 缺少类型: {missing}"
    stale = [name for name in ("housing-timeseries",) if name in config]
    assert not stale, f"openspec/config.yaml 仍含已移除类型: {stale}"
