"""测试夹具：导入位于 src/ 的 m2v 包与 skill 脚本目录。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
SCRIPT_TOOLS_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "material2video" / "scripts"
sys.path.insert(0, str(SCRIPT_TOOLS_DIR))

from m2v.core.workspace import PROJECT_MARKER

SKILL_MARKER = PROJECT_MARKER

#: 默认不收集的慢速层。日常验证只跑纯单元与契约用例；需要分层时显式选择。
DEFAULT_EXCLUDED_MARKERS = ("slow", "media")


def pytest_addoption(parser):
    parser.addoption(
        "--full",
        action="store_true",
        help="运行全部用例，包括默认排除的 slow 与 media",
    )


def pytest_collection_modifyitems(config, items):
    """未指定目标或 `-m` 时按层排除慢速用例；显式选择或显式路径完全交给调用方。"""
    if config.getoption("--full") or config.getoption("markexpr") or _has_explicit_path(config):
        return
    selected, deselected = [], []
    for item in items:
        if any(item.get_closest_marker(name) for name in DEFAULT_EXCLUDED_MARKERS):
            deselected.append(item)
        else:
            selected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


def _has_explicit_path(config) -> bool:
    """命令行里点名了存在的测试路径（含 `file.py::test` 形式）时，不套用默认排除。"""
    for argument in config.invocation_params.args:
        if argument.startswith("-"):
            continue
        if Path(argument.split("::", 1)[0]).exists():
            return True
    return False


@pytest.fixture(scope="session")
def chromium_ready():
    """浏览器不可用时跳过，而不是让整个测试套件失败。"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
    except Exception as exc:  # noqa: BLE001 - 任何启动失败都应降级为跳过
        pytest.skip(f"未安装可用的 Playwright Chromium: {exc}")


def create_typed_project(directory: str | Path, video_type: str) -> Path:
    """按类型目录创建作品，替代测试里另写一份材料映射的旧用法。

    材料入口的唯一来源是 ``m2v.types.catalog``；测试也走同一条路径，因此目录里
    的文件名一旦变化，用例会跟着失败，而不是悄悄与实现错位。
    """
    from m2v.core.project import create_project
    from m2v.types import catalog

    return create_project(directory, video_type, catalog.catalog().get(video_type).material_map())


def register_synthetic_type(monkeypatch, name: str, description: str = "合成类型") -> None:
    """为测试用的合成类型补一份类型目录登记项。

    类型身份只在类型目录里维护，因此走统一入口的合成类型同样需要登记；这里只替换
    进程内缓存，不写仓库文件。
    """
    from m2v.types import catalog

    entry = catalog.Entry(
        name=name,
        description=description,
        summary=description,
        plan=description,
        skill_guide=description,
        materials=(
            catalog.Material(name="material", file="material.json", template={"schemaVersion": 1}),
        ),
    )
    current = catalog.catalog()
    monkeypatch.setattr(catalog, "_cached",
                        catalog.Catalog(current.entries() + (entry,), current.categories()))
