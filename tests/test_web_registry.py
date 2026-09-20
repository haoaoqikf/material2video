"""注册表生成物的一致性机检（能力：react-component-registry）。

组件集合的唯一真源是 `web/src/registry/registry.json`；三份派生文件由
`scripts/sync_catalog.py` 生成：

- `scripts/a2v/catalog.py` 的生成区（校验器镜像）；
- `references/figure-catalog.md` 的组件表（给上游 AI 的文档）；
- `web/src/schema/figureKinds.ts`（分镜 schema 的 kind 枚举）。

这里检查四类性质：

1. **重新生成无差异**——注册表改动而派生文件没有重新生成时，逐文件指名（任务 9.2）；
2. **注册表自洽**——默认映射只指向已实现组件、默认组件声明了适用场景、
   场景类型是分镜校验器认识的类型、实现源码真实存在；
3. **声明了却不画的标注键**——labels 里的每个键必须出现在组件实现源码里；
   反向（画了却没声明）同样失败，并指出键与文件（任务 9.3）；
4. **渲染层真的消费了注册表**——渲染层一側（vitest）由
   `web/src/registry/registry.test.ts` 承担，这里不重复。

生成机制建立之前，catalog.py 与浏览器端注册表各抄一份、靠文本解析对照，
漂移只能等测试失败才暴露；现在漂移在「重新生成无差异」上失败。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents" / "skills" / "article2video" / "scripts"
REGISTRY = ROOT / "web" / "src" / "registry" / "registry.json"
WEB_SRC = ROOT / "web" / "src"

sys.path.insert(0, str(SCRIPTS))

import sync_catalog  # noqa: E402

from a2v import catalog  # noqa: E402
from a2v import storyboard as storyboard_validator  # noqa: E402


@pytest.fixture(scope="module")
def registry() -> dict:
    return sync_catalog.load_registry()


# ---------------------------------------------------------------- 重新生成无差异


def test_regenerated_outputs_match_the_disk(registry: dict) -> None:
    """注册表改了而派生文件没重新生成时，机检失败并逐个指名落后的文件。"""
    expected = sync_catalog.build_outputs(registry)
    drifted = []
    for path, content in expected.items():
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        if actual != content:
            drifted.append(str(path.relative_to(ROOT)))
    assert not drifted, (
        "以下派生文件与注册表不一致，重新生成后再提交"
        "（uv run python .agents/skills/article2video/scripts/sync_catalog.py）：\n  "
        + "\n  ".join(drifted)
    )


def test_catalog_generated_region_is_complete(registry: dict) -> None:
    """校验器镜像必须覆盖注册表里的全部组件，一个不多一个不少。"""
    kinds = set(registry["figures"] and [entry["kind"] for entry in registry["figures"]])
    assert kinds == set(catalog.FIGURE_CATALOG)
    assert catalog.DEFAULT_KINDS == registry["defaultKindByScene"]


# ---------------------------------------------------------------- 注册表自洽


def test_defaults_point_to_implemented_components(registry: dict) -> None:
    entries = {entry["kind"]: entry for entry in registry["figures"]}
    for scene_type, kind in registry["defaultKindByScene"].items():
        entry = entries.get(kind)
        assert entry, f"{scene_type} 默认到不存在的组件 {kind}"
        assert entry["implemented"], f"{kind} 还没实现，不能当 {scene_type} 的默认"


def test_default_kind_declares_its_scene_type(registry: dict) -> None:
    for scene_type, kind in registry["defaultKindByScene"].items():
        entry = next(item for item in registry["figures"] if item["kind"] == kind)
        assert scene_type in entry["sceneTypes"], (
            f"{kind} 是 {scene_type} 的默认，但 registry.json 的 sceneTypes 没有声明它"
        )


def test_scene_types_are_known_scene_types(registry: dict) -> None:
    known = set(storyboard_validator._SCENE_FIELDS)
    for entry in registry["figures"]:
        unknown = sorted(set(entry["sceneTypes"]) - known)
        assert not unknown, (
            f"{entry['kind']} 声明了不存在的场景类型：{unknown}（已知：{sorted(known)}）"
        )


def test_every_implemented_component_source_exists(registry: dict) -> None:
    for entry in registry["figures"]:
        if not entry["implemented"]:
            continue
        path = WEB_SRC / entry["source"]
        assert path.is_file(), f"{entry['kind']} 的实现源码不存在：{path}"


def test_canvas_and_schematic_flags_drive_the_validator_mirror(registry: dict) -> None:
    """catalog 的两份清单是注册表布尔旗标的投影，不是第三份手抄。"""
    canvas = {entry["kind"] for entry in registry["figures"] if entry.get("canvasDrawn")}
    schematic = {entry["kind"] for entry in registry["figures"] if entry.get("schematicMark")}
    assert canvas == set(catalog.CANVAS_KINDS)
    assert schematic == set(catalog.SCHEMATIC_KINDS)


# ---------------------------------------------------------------- 声明了却不画的标注键（任务 9.3）

#: 组件读取标注键的唯一形态：`labels['键']` / `ann['键']` / `spec.labels['键']`。
#: 出现新的接收名时把它加进来——机检跟着真实写法走。
_LABEL_ACCESS = re.compile(
    r"\b(?:fig\.spec\.labels|spec\.labels|labels|ann)\['([A-Za-z][\w-]*)'\]"
)


def test_declared_labels_are_actually_drawn(registry: dict) -> None:
    """声明了却不画的键：分镜写了、校验器放行、画面上什么都没有——机检必须拦住。"""
    offenders: list[str] = []
    for entry in registry["figures"]:
        if not entry["implemented"] or not entry["labels"]:
            continue
        source = (WEB_SRC / entry["source"]).read_text(encoding="utf-8")
        for key in entry["labels"]:
            if not re.search(rf"['\"]{re.escape(key)}['\"]", source):
                offenders.append(
                    f"{entry['kind']} 声明了标注键 {key}，但 {entry['source']} 里从来没有画它"
                )
    assert not offenders, "\n  ".join(offenders)


def test_drawn_labels_are_declared(registry: dict) -> None:
    """反向同样成立：组件画出来的键必须在注册表里声明过，否则校验器管不到它。"""
    offenders: list[str] = []
    for entry in registry["figures"]:
        if not entry["implemented"]:
            continue
        source = (WEB_SRC / entry["source"]).read_text(encoding="utf-8")
        declared = set(entry["labels"])
        for key in _LABEL_ACCESS.findall(source):
            if key not in declared:
                offenders.append(
                    f"{entry['kind']} 画了标注键 {key}，但 registry.json 没有声明它"
                    f"（{entry['source']}）"
                )
    assert not offenders, "\n  ".join(offenders)


def test_label_check_is_alive() -> None:
    """机检自身的哨兵：正则一旦失效（比如组件换了读取写法），这里先失败。"""
    sample = "const labels = fig.spec.labels;\nconst unit = labels['unit'];"
    assert _LABEL_ACCESS.findall(sample) == ["unit"]
