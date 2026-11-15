"""仓库与 skill bundle 定位。"""
from __future__ import annotations

from pathlib import Path

#: skill bundle 自身的位置。由本文件位置推出，与仓库放在哪里无关。
REPOSITORY_ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / ".git").exists() and (parent / "pyproject.toml").is_file()
)
BUNDLE_DIR = REPOSITORY_ROOT / ".agents" / "skills" / "material2video"
