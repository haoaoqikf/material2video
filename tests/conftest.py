"""测试夹具：导入位于 src/ 的 m2v 包与 skill 脚本目录。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
SCRIPT_TOOLS_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "material2video" / "scripts"
sys.path.insert(0, str(SCRIPT_TOOLS_DIR))
# 作品运行时以模板为唯一实现；相关测试直接导入模板副本，不依赖主项目保留同名模块。
TEMPLATE_RUNTIME = Path(__file__).resolve().parents[1] / "templates" / "standalone" / "runtime" / "python"
sys.path.insert(0, str(TEMPLATE_RUNTIME))

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
    """路径选择不放开成本层；只有明确点名的节点、标记或 --full 可以放开。"""
    if config.getoption("--full") or config.getoption("markexpr"):
        return
    nodes = [(Path(parts[0]).resolve(), parts[1:])
             for argument in config.args if len(parts := argument.split("::")) > 1]
    selected, deselected = [], []
    for item in items:
        explicit = any(
            item.path.resolve() == path and len(selectors) <= len(actual := item.nodeid.split("::")[1:])
            and all(wanted == found or wanted == found.split("[", 1)[0]
                    for wanted, found in zip(selectors, actual))
            for path, selectors in nodes
        )
        if not explicit and any(item.get_closest_marker(name) for name in DEFAULT_EXCLUDED_MARKERS):
            deselected.append(item)
        else:
            selected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


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

    材料入口的唯一来源是 ``m2v.type_system.catalog``；测试也走同一条路径，因此目录里
    的文件名一旦变化，用例会跟着失败，而不是悄悄与实现错位。
    """
    from m2v.core.project import create_project
    from m2v.type_system import catalog

    return create_project(directory, video_type, catalog.catalog().get(video_type).material_map())
