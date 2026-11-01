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
    "schemaVersion": 2,
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
    documented = catalog_module.catalog()
    expected = {}
    for entry in documented.entries():
        category = documented.category(entry.category) if entry.category else None
        expected[entry.name] = {
            "description": entry.description,
            "category": category.id if category else None,
            "categoryTitle": category.title if category else None,
        }
    assert {item["type"]: {key: item[key] for key in ("description", "category", "categoryTitle")}
            for item in listed} == expected


def test_categories_group_types_and_derive_workspace_parts() -> None:
    documented = catalog_module.catalog()
    assert [category.id for category in documented.categories()] == ["route-journey"]
    assert [entry.name for entry in documented.types_in("route-journey")] == ["driving-route", "road-trip"]
    assert documented.get("driving-route").workspace_parts() == ("route-journey", "driving-route")
    assert documented.get("general").workspace_parts() == ("general",)
    assert {entry.name for entry in documented.uncategorized()} == {
        "financial-timeseries", "general", "building-construction", "vehicle-showcase",
    }


def test_category_name_is_not_a_video_type() -> None:
    with pytest.raises(M2VError, match="类型类别「路线旅程」"):
        registry.get("route-journey")


def test_docs_type_lists_match_the_catalog() -> None:
    """三份文档里的类型清单必须是生成结果；漂移时用 `sync_docs.py` 重新生成。"""
    outputs = sync_docs.build_outputs(include_production=False)
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
    (lambda payload: payload.update(schemaVersion=3), "schemaVersion"),
    (lambda payload: payload.update(types=[]), "types 必须是非空数组"),
    (lambda payload: payload["types"].append(json.loads(json.dumps(payload["types"][0]))), "重复登记类型"),
    (lambda payload: payload["types"][0].update(summary="   "), "summary 必须是非空字符串"),
    (lambda payload: payload["types"][0].update(name="Bad Name"), "小写字母"),
    (lambda payload: payload["types"][0].update(materials=[]), "materials 必须是非空数组"),
    (lambda payload: payload["types"][0]["materials"][0].update(file="../escape.json"), "单个 JSON 文件名"),
    (lambda payload: payload["types"][0]["materials"][0].update(template={}), "template 必须是非空对象"),
    (lambda payload: payload["types"][0].update(starters=["../escape.tsx"]), "相对 .tsx 路径"),
    (lambda payload: payload["types"][0].update(starters=["scenes/x.ts", "scenes/y.tsx"]), "相对 .tsx 路径"),
    (lambda payload: payload["types"][0].update(starters=[]), "必须是非空数组"),
    (lambda payload: payload["types"][0].update(category="ghost"), "未登记的类别"),
    (lambda payload: payload.update(categories=[]), "categories 必须是非空数组"),
    (lambda payload: payload.update(categories=[{"id": "solo", "title": "单", "description": "说明"}]),
     "没有任何类型成员"),
    (lambda payload: payload.update(categories=[{"id": "demo", "title": "示例", "description": "说明"}]),
     "类别标识与类型名冲突"),
    (lambda payload: payload.update(categories=[
        {"id": "group", "title": "组", "description": "说明"},
        {"id": "group", "title": "组二", "description": "说明二"},
    ]), "重复登记类别"),
    (lambda payload: payload.update(categories=[{"id": "Bad", "title": "组", "description": "说明"}]),
     "小写字母"),
], ids=["版本不符", "空类型表", "重复类型", "空文案", "非法类型名", "空材料表", "越界文件名", "空模板",
        "起步文件越界", "起步文件非 tsx", "起步文件空表", "未登记类别", "空类别表", "空类别",
        "类别与类型同名", "重复类别", "非法类别名"])
def test_invalid_catalog_is_rejected_at_load(tmp_path: Path, mutate, message: str) -> None:
    with pytest.raises(M2VError, match=message):
        catalog_module.load(_write_catalog(tmp_path, mutate))


def test_catalog_groups_types_by_category(tmp_path: Path) -> None:
    def mutate(payload):
        payload["types"][0].update(category="group")
        payload["categories"] = [{"id": "group", "title": "示例类别", "description": "说明"}]

    loaded = catalog_module.load(_write_catalog(tmp_path, mutate))
    assert loaded.get("demo").workspace_parts() == ("group", "demo")
    assert loaded.types_in("group")[0].name == "demo"


def test_init_places_categorized_type_under_its_category(tmp_path: Path, capsys) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "driving-route", "--project", "demo", "--content-root", str(root)]) == 0
    capsys.readouterr()
    assert (root / "videos/route-journey/driving-route/demo/project.json").is_file()
    assert not (root / "videos/driving-route/demo").exists()
    assert main(["init", "--type", "road-trip", "--project", "videos/route-journey/road-trip/trip",
                 "--content-root", str(root)]) == 0
    capsys.readouterr()
    assert (root / "videos/route-journey/road-trip/trip/project.json").is_file()


def test_init_rejects_flat_path_for_categorized_type(tmp_path: Path, capsys) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "driving-route", "--project", "videos/driving-route/demo",
                 "--content-root", str(root)]) == 2
    message = capsys.readouterr().err
    assert "videos/route-journey/driving-route/<slug>" in message
    assert not (root / "videos/driving-route/demo").exists()


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


def test_general_init_writes_a_v8_storyboard(tmp_path: Path, capsys) -> None:
    root = _init(tmp_path, "general")
    capsys.readouterr()
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    assert {"version", "schemaVersion", "fps", "width", "height", "title", "scenes"} <= set(storyboard)
    assert storyboard["version"] == 8 and storyboard["schemaVersion"] == 8
    # 默认显式横屏；画幅可以删掉整对尺寸回落到默认，但不能只写一边。
    assert (storyboard["width"], storyboard["height"]) == (1920, 1080)
    assert storyboard["input"] == {"kind": "article"} and storyboard["targetSeconds"] == 60
    assert [scene["template"] for scene in storyboard["scenes"]] == ["code"]
    (root / "article.md").write_text("填写观点。", encoding="utf-8")
    assert main(["validate", "--project", str(root)]) == 0


def test_init_writes_the_declared_starter_files(tmp_path: Path, capsys) -> None:
    """起步文件同样按目录声明写入：本地代码场景入口必须存在，validate 才可能通过。"""
    for entry in catalog_module.catalog().entries():
        root = _init(tmp_path, entry.name)
        capsys.readouterr()
        for relative in entry.starters:
            assert (root / relative).is_file(), f"{entry.name} 缺少起步文件 {relative}"
            assert (catalog_module.starters_dir(entry.name) / relative).is_file()
    assert catalog_module.catalog().get("general").starters == ("scenes/opening.tsx",)


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
