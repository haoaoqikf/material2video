"""通用类型替换：入口、材料与过期产物不能混用旧编排契约。"""
import json

import pytest

from m2v.cli import main, _register_builtins
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_current_prepared, load_project
from m2v.type_system import registry
from m2v.types.general import adapter, explainer
from helpers.general import board, fake_record, fake_tts, project, scene_root


def test_current_types_are_listed(capsys):
    assert main(["types"]) == 0
    types = {item["type"]: item["description"] for item in json.loads(capsys.readouterr().out)}
    assert set(types) == {"general", "financial-timeseries", "driving-route",
                          "building-construction", "road-trip", "vehicle-showcase"}
    assert types["general"] == "通用"
    assert types["driving-route"] == "自驾路线动画"


def test_removed_housing_type_cannot_be_initialized(tmp_path, capsys):
    target = tmp_path / "removed"
    assert main(["init", "--type", "housing-timeseries", "--project", str(target)]) == 2
    assert "未知视频类型：housing-timeseries" in capsys.readouterr().err
    assert not target.exists()


@pytest.mark.parametrize("command", ["validate", "prepare", "preview", "render", "review-template", "review", "status"])
def test_removed_housing_project_is_rejected_without_outputs(tmp_path, capsys, command):
    # 保留旧清单的输入形状，验证拒绝来自类型退役，而不是材料缺失。
    create_project(tmp_path, "housing-timeseries", {"series": "series.json"})
    (tmp_path / "series.json").write_text("{}", encoding="utf-8")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert main([command, "--project", str(tmp_path)]) == 1
    assert "未知视频类型：housing-timeseries" in capsys.readouterr().err
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before
    assert not (tmp_path / "outputs").exists()


def test_legacy_identity_and_command_are_rejected(tmp_path):
    _register_builtins()
    with pytest.raises(M2VError, match="未知视频类型"):
        registry.get("article-narrative")
    assert main(["init", "--type", "article-narrative", "--project", str(tmp_path / "legacy")]) == 2
    with pytest.raises(SystemExit) as error:
        main(["article", "status"])
    assert error.value.code == 2
    assert not (tmp_path / "legacy").exists()


def test_general_init_has_only_v8_storyboard(tmp_path):
    assert main(["init", "--type", "general", "--project", "demo", "--content-root", str(tmp_path)]) == 0
    root, manifest = load_project(tmp_path / "videos/general/demo")
    assert manifest["materials"] == {"storyboard": "storyboard.json"}
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    assert storyboard["version"] == 8 and (storyboard["width"], storyboard["height"]) == (1920, 1080)
    assert (manifest["output"]["width"], manifest["output"]["height"]) == (storyboard["width"], storyboard["height"])
    # 初始化同时生成可运行的本地场景入口：材料写得出，画面也录得起来。
    assert (root / "scenes/opening.tsx").is_file()
    assert not (root / "general-plan.json").exists()


def test_general_rejects_old_plan_material(tmp_path):
    create_project(tmp_path, "general", {"plan": "general-plan.json"})
    (tmp_path / "general-plan.json").write_text('{"schemaVersion":1,"scenes":[]}', encoding="utf-8")
    root, manifest = load_project(tmp_path)
    with pytest.raises(M2VError, match="materials.storyboard"):
        adapter.validate(root, manifest)


@pytest.mark.parametrize("field,value", [("renderer", {"kind": "code", "module": "entry"}),
                                         ("type", "financial-timeseries"), ("project", "../child")])
def test_general_rejects_unknown_scene_fields(tmp_path, field, value):
    data = board()
    data["scenes"][0][field] = value
    with pytest.raises(M2VError, match="未知字段"):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.media
def test_preparation_for_old_type_cannot_authorize_general(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch); fake_record(monkeypatch)
    legacy = {**manifest, "type": "article-narrative"}
    adapter.prepare(root, legacy)
    with pytest.raises(M2VError, match="与当前作品不匹配"):
        load_current_prepared(root, manifest)
