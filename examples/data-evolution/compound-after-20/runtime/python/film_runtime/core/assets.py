"""作品本地资源定位与指纹键；只在本工程范围解析，不查找主项目或Git目录。"""

from __future__ import annotations

from pathlib import Path

#: skill bundle 自身的位置。由本文件位置推出，与仓库放在哪里无关。
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def default_mounts() -> dict[str, Path]:
    """默认挂载表：别名前缀 → 挂载目录，当前为空表。

    共享资产别名已随整页组件路径移除：契约页与前端工程资产由
    `contract_page.web_mounts()` 显式给出。这里保留空表作为扩展点——
    服务器与扫描器读同一份表，避免「服务器映射到 A、扫描器按 B 找」
    这类只在渲染时才暴露的漂移。
    """
    return {}


def mount_key(path: Path, mounts: dict[str, Path] | None = None) -> str | None:
    """文件落在挂载目录内时对应的别名键（`__m2v_web__/styles/tokens.css`）。

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
