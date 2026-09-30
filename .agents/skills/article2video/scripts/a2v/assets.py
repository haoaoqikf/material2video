"""网页引用的本地资源定位。

渲染前置扫描与指纹复核都要回答同一个问题：「这个页面实际加载了哪些
本地样式与脚本」。放在这里共用，避免两处各写一遍路径推导而慢慢走偏。

React/Remotion 时代页面上只剩契约页（在仓库 `web/` 里），共享资产别名
挂载已随旧资产一并移除；这里保留的引用扫描、项目根界定与指纹键推导
供溯源复核与体检使用。
"""

from __future__ import annotations

import re
from pathlib import Path

#: 项目根标记：用于界定「可以读的本地资源」范围
PROJECT_MARKERS = (".git", "pyproject.toml")

#: skill bundle 自身的位置。由本文件位置推出，与仓库放在哪里无关。
BUNDLE_DIR = Path(__file__).resolve().parents[2]

#: 共享资产的服务器别名前缀
SKILL_MOUNT = "/__a2v__"

_ASSET_REFERENCE = re.compile(
    r"""<(?:link[^>]+href|script[^>]+src)=["']([^"']+\.(?:css|js))["']""",
    re.IGNORECASE,
)


def default_mounts() -> dict[str, Path]:
    """默认挂载表：别名前缀 → 挂载目录，当前为空表。

    共享资产别名已随整页组件路径移除：契约页与前端工程资产由
    `contract_page.web_mounts()` 显式给出。这里保留空表作为扩展点——
    服务器与扫描器读同一份表，避免「服务器映射到 A、扫描器按 B 找」
    这类只在渲染时才暴露的漂移。
    """
    return {}


def project_root(start: Path) -> Path | None:
    """从起始目录向上找项目根，用来界定「可以扫描的本地资源」。

    共享资产（如 skill 的 assets/）通常不在网页目录内，只按网页目录判断会漏扫；
    但也不能顺着相对路径读到仓库外的任意文件，因此以项目标记为界。
    别名引用不走这条判断：它的目标目录由挂载表给定，是明确允许的范围。
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def _match_mount(reference: str, mounts: dict[str, Path]) -> tuple[str, Path] | None:
    """别名引用 → (前缀, 挂载目录)；不是别名引用或越界时返回 None。"""
    for prefix, directory in mounts.items():
        base = prefix.rstrip("/")
        if reference != base and not reference.startswith(base + "/"):
            continue
        resolved = Path(directory).resolve()
        relative = reference[len(base) :].lstrip("/")
        candidate = (resolved / relative).resolve()
        if candidate != resolved and resolved not in candidate.parents:
            return None  # 越界：不读挂载目录之外的文件
        return prefix, resolved
    return None


def mount_key(path: Path, mounts: dict[str, Path] | None = None) -> str | None:
    """文件落在挂载目录内时对应的别名键（`__a2v_web__/styles/tokens.css`）。

    键按**文件位置**判定，而不是按引用写法：内容根里的页面用相对路径引用
    共享资产，但这些文件仍在仓库 `web/` 里，因此只能靠别名记——否则指纹里
    只剩一个文件名，工作区根下拼不出来，复核会把每一份内容根成片都判成
    「资产不见了」。
    """
    for prefix, directory in (default_mounts() if mounts is None else mounts).items():
        try:
            relative = path.resolve().relative_to(Path(directory).resolve())
        except ValueError:
            continue
        return f"{prefix.strip('/')}/{relative.as_posix()}"
    return None


def asset_key(
    path: Path,
    workspace_root: Path,
    mounts: dict[str, Path] | None = None,
) -> str:
    """一个被引用的本地文件在指纹里的键。

    别名目录里的文件记别名键（与内容根、仓库的位置都无关）；其余相对工作区根
    记；工作区根之外退回文件名——产物里不写绝对路径。
    """
    key = mount_key(path, mounts)
    if key is not None:
        return key
    try:
        return path.resolve().relative_to(Path(workspace_root).resolve()).as_posix()
    except ValueError:
        return path.name


def key_path(key: str, workspace_root: Path, mounts: dict[str, Path] | None = None) -> Path | None:
    """指纹键 → 真实路径，供陈旧判定复核。

    别名键按**运行中的** skill 资产目录解析；越界的键（例如被人手改过的
    溯源文件）返回 None，让调用方按「文件不见了」处理。
    """
    cleaned = key.lstrip("/")
    for prefix, directory in (default_mounts() if mounts is None else mounts).items():
        base = prefix.strip("/")  # 键里不带前导斜杠：`__a2v__/base.css`
        if cleaned != base and not cleaned.startswith(base + "/"):
            continue
        resolved = Path(directory).resolve()
        candidate = (resolved / cleaned[len(base) :].lstrip("/")).resolve()
        if candidate != resolved and resolved not in candidate.parents:
            return None
        return candidate
    return Path(workspace_root) / key


def local_assets(
    page: Path, html: str, mounts: dict[str, Path] | None = None
) -> list[tuple[str, Path]]:
    """收集网页引用到的本地样式表与脚本，跳过远程与项目范围外的路径。

    别名引用按挂载表解析：内容根里的页面正是用别名引用共享资产，扫描若不
    跟着走，把动效写进共享组件库就能绕过渲染前的静态检查。
    """
    resolved_mounts = default_mounts() if mounts is None else mounts
    root = project_root(page.parent)
    found: list[tuple[str, Path]] = []
    for reference in _ASSET_REFERENCE.findall(html):
        if reference.startswith(("http://", "https://", "//")):
            continue
        clean = reference.split("?")[0].split("#")[0]
        match = _match_mount(clean, resolved_mounts)
        if match is not None:
            prefix, directory = match
            candidate = (directory / clean[len(prefix.rstrip("/")) :].lstrip("/")).resolve()
            if candidate.is_file():
                found.append((reference, candidate))
            continue
        candidate = (page.parent / clean).resolve()
        if not candidate.is_file():
            continue
        inside_page_dir = page.parent.resolve() in candidate.parents
        inside_project = root is not None and root in candidate.parents
        if not (inside_page_dir or inside_project):
            continue
        found.append((reference, candidate))
    return found
