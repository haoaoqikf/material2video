"""网页引用的本地资源定位。

渲染前置扫描与设计宪法检查都要回答同一个问题：「这个网页实际加载了哪些
本地样式与脚本」。放在这里共用，避免两处各写一遍路径推导而慢慢走偏。
"""

from __future__ import annotations

import re
from pathlib import Path

#: 项目根标记：用于界定「可以读的本地资源」范围
PROJECT_MARKERS = (".git", "pyproject.toml")

_ASSET_REFERENCE = re.compile(
    r"""<(?:link[^>]+href|script[^>]+src)=["']([^"']+\.(?:css|js))["']""",
    re.IGNORECASE,
)


def project_root(start: Path) -> Path | None:
    """从起始目录向上找项目根，用来界定「可以扫描的本地资源」。

    共享资产（如 skill 的 assets/）通常不在网页目录内，只按网页目录判断会漏扫；
    但也不能顺着相对路径读到仓库外的任意文件，因此以项目标记为界。
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def local_assets(page: Path, html: str) -> list[tuple[str, Path]]:
    """收集网页引用到的本地样式表与脚本，跳过远程与项目范围外的路径。"""
    root = project_root(page.parent)
    found: list[tuple[str, Path]] = []
    for reference in _ASSET_REFERENCE.findall(html):
        if reference.startswith(("http://", "https://", "//")):
            continue
        candidate = (page.parent / reference.split("?")[0].split("#")[0]).resolve()
        if not candidate.is_file():
            continue
        inside_page_dir = page.parent.resolve() in candidate.parents
        inside_project = root is not None and root in candidate.parents
        if not (inside_page_dir or inside_project):
            continue
        found.append((reference, candidate))
    return found
