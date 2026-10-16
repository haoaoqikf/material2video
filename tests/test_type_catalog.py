"""类型目录作为单一来源的约束：代码派生、文档生成与初始化产物。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sync_docs
from m2v.cli import _register_builtins, main
from m2v.core.errors import M2VError
from m2v.types import catalog as catalog_module
from m2v.types import registry
from m2v.types.registry import VideoType

DOCS = ("README.md", ".agents/skills/material2video/SKILL.md", "docs/PROJECT_PLAN.md")


VALID_CATALOG = {
    "schemaVersion": 1,
    "types": [{
        "name": "demo",
        "description": "一句话说明",
        "summary": "README 文案",
        "plan": "规划文案",
        "skillGuide": "Skill 指导",
        "materials": [{"name": "material", "file": "material.json", "template": {"schemaVersion": 1}}],
    }],
}


def _write_catalog(tmp_path: Path, mutate) -> Path:
    payload = json.loads(json.dumps(VALID_CATALOG, ensure_ascii=False))
    mutate(payload)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _init(tmp_path: Path, video_type: str) -> Path:
    root = tmp_path / video_type
    assert main(["init", "--type", video_type, "--project", str(root)]) == 0
    return root


def test_catalog_and_registry_describe_the_same_types() -> None:
    """目录与注册表必须一一对应：任一侧多出或少掉一个类型都要失败。"""
    _register_builtins()
    assert set(catalog_module.catalog().names()) == {item.name for item in registry.all_types()}


def test_registered_type_missing_from_catalog_is_rejected(monkeypatch) -> None:
    """「未登记」不是静默降级：使用该类型的操作在渲染前失败并指出登记位置。"""
    monkeypatch.setattr(registry, "_registry", {})
    noop = lambda *_args, **_kwargs: None
    registry.register(VideoType("ghost", noop, noop, noop, noop))
    with pytest.raises(M2VError, match="未在类型目录登记"):
        registry.get("ghost")
    assert registry.describe("ghost") == registry.UNREGISTERED_DESCRIPTION


def test_types_command_reads_descriptions_from_the_catalog(capsys) -> None:
    assert main(["types"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert {item["type"]: item["description"] for item in listed} == {
        entry.name: entry.description for entry in catalog_module.catalog().entries()
    }


def test_docs_type_lists_match_the_catalog() -> None:
    """三份文档里的类型清单必须是生成结果；漂移时用 `sync_docs.py` 重新生成。"""
    outputs = sync_docs.build_outputs()
    assert set(outputs) == set(DOCS)
    for relative, generated in outputs.items():
        current, _ = sync_docs.read_text(relative)
        assert current == generated, f"{relative} 的类型清单与类型目录不一致"


def test_generator_replaces_only_the_marked_region() -> None:
    text = f"头部\n{sync_docs.START_MARK}\n- 旧清单\n{sync_docs.END_MARK}\n尾部\n"
    assert sync_docs._inject("示例.md", text, ["- `demo`：新说明"]) == (
        f"头部\n{sync_docs.START_MARK}\n- `demo`：新说明\n{sync_docs.END_MARK}\n尾部\n"
    )


@pytest.mark.parametrize("text, message", [
    ("没有标记的文档\n", "恰好一对生成标记"),
    (f"{sync_docs.START_MARK}\n- 手工清单\n", "恰好一对生成标记"),
    (f"{sync_docs.START_MARK}\n{sync_docs.START_MARK}\n{sync_docs.END_MARK}\n", "恰好一对生成标记"),
    (f"{sync_docs.END_MARK}\n{sync_docs.START_MARK}\n", "顺序颠倒"),
], ids=["无标记", "只有起始标记", "重复起始标记", "标记顺序颠倒"])
def test_generator_rejects_documents_without_a_single_marker_pair(text: str, message: str) -> None:
    with pytest.raises(M2VError, match=message):
        sync_docs._inject("示例.md", text, ["- `demo`：说明"])


def test_valid_catalog_loads_in_declaration_order(tmp_path: Path) -> None:
    loaded = catalog_module.load(_write_catalog(tmp_path, lambda payload: None))
    assert loaded.names() == ("demo",)
    assert loaded.get("demo").material_map() == {"material": "material.json"}


@pytest.mark.parametrize("mutate, message", [
    (lambda payload: payload.update(schemaVersion=2), "schemaVersion"),
    (lambda payload: payload.update(types=[]), "types 必须是非空数组"),
    (lambda payload: payload["types"].append(json.loads(json.dumps(payload["types"][0]))), "重复登记类型"),
    (lambda payload: payload["types"][0].update(summary="   "), "summary 必须是非空字符串"),
    (lambda payload: payload["types"][0].update(name="Bad Name"), "小写字母"),
    (lambda payload: payload["types"][0].update(materials=[]), "materials 必须是非空数组"),
    (lambda payload: payload["types"][0]["materials"][0].update(file="../escape.json"), "单个 JSON 文件名"),
    (lambda payload: payload["types"][0]["materials"][0].update(template={}), "template 必须是非空对象"),
], ids=["版本不符", "空类型表", "重复类型", "空文案", "非法类型名", "空材料表", "越界文件名", "空模板"])
def test_invalid_catalog_is_rejected_at_load(tmp_path: Path, mutate, message: str) -> None:
    with pytest.raises(M2VError, match=message):
        catalog_module.load(_write_catalog(tmp_path, mutate))


def test_init_writes_exactly_the_materials_declared_by_the_catalog(tmp_path: Path, capsys) -> None:
    for entry in catalog_module.catalog().entries():
        root = _init(tmp_path, entry.name)
        capsys.readouterr()
        for material in entry.materials:
            assert (root / material.file).is_file(), f"{entry.name} 缺少 {material.file}"
            data = json.loads((root / material.file).read_text(encoding="utf-8"))
            # 材料内容被文件名键包裹是本次修掉的缺陷形态，不能再出现。
            assert material.file not in data, f"{entry.name} 的 {material.file} 被文件名键包裹"
            assert set(data) == set(material.template), f"{entry.name} 的 {material.file} 顶层结构与目录不一致"
        declared = set(entry.material_map().values())
        written = {path.name for path in root.iterdir() if path.suffix == ".json"}
        assert written == declared | {"project.json"}


def test_article_init_writes_a_v6_storyboard(tmp_path: Path, capsys) -> None:
    root = _init(tmp_path, "general")
    capsys.readouterr()
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    assert {"version", "schemaVersion", "fps", "width", "height", "title", "scenes"} <= set(storyboard)
    assert storyboard["version"] == 6 and storyboard["schemaVersion"] == 6
    assert storyboard["input"] == {"kind": "article"} and storyboard["targetSeconds"] == 60
    (root / "article.md").write_text("填写观点。", encoding="utf-8")
    assert main(["validate", "--project", str(root)]) == 0


def test_financial_material_constants_agree_with_the_catalog(tmp_path: Path) -> None:
    """金融类型里自带的两份文件清单若与目录分叉，本用例会失败。"""
    from m2v.types.financial import adapter as financial_adapter
    from m2v.types.financial import financial

    entry = catalog_module.catalog().get("financial-timeseries")
    assert [material.name for material in entry.materials] == ["request", "prices", "plan"]
    assert tuple(material.file for material in entry.materials) == financial.MATERIALS

    root = tmp_path / "financial"
    root.mkdir()
    with pytest.raises(M2VError) as excinfo:
        financial_adapter._load(root, {"materials": entry.material_map()})
    assert "材料入口固定为" not in str(excinfo.value)
    with pytest.raises(M2VError, match="材料入口固定为"):
        financial_adapter._load(root, {"materials": {"request": "request.json"}})
