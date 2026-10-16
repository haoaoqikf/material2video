"""通用类型替换：入口、材料与过期产物不能混用旧编排契约。"""
import json

import pytest

from m2v.cli import main, _register_builtins
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_current_prepared, load_project
from m2v.types import registry
from m2v.types.general import adapter, explainer
from test_article_explainer import board, fake_tts, project


def test_only_three_current_types(capsys):
    assert main(["types"]) == 0
    types = {item["type"]: item["description"] for item in json.loads(capsys.readouterr().out)}
    assert set(types) == {"general", "financial-timeseries", "housing-timeseries"}
    assert types["general"] == "通用"


def test_legacy_identity_and_command_are_rejected(tmp_path):
    _register_builtins()
    with pytest.raises(M2VError, match="未知视频类型"):
        registry.get("article-narrative")
    assert main(["init", "--type", "article-narrative", "--project", str(tmp_path / "legacy")]) == 2
    with pytest.raises(SystemExit) as error:
        main(["article", "status"])
    assert error.value.code == 2
    assert not (tmp_path / "legacy").exists()


def test_general_init_has_only_v6_storyboard(tmp_path):
    assert main(["init", "--type", "general", "--project", "demo", "--content-root", str(tmp_path)]) == 0
    root, manifest = load_project(tmp_path / "videos/general/demo")
    assert manifest["materials"] == {"storyboard": "storyboard.json"}
    assert json.loads((root / "storyboard.json").read_text(encoding="utf-8"))["version"] == 6
    assert not (root / "general-plan.json").exists()


def test_general_rejects_old_plan_material(tmp_path):
    create_project(tmp_path, "general", {"plan": "general-plan.json"})
    (tmp_path / "general-plan.json").write_text('{"schemaVersion":1,"scenes":[]}', encoding="utf-8")
    root, manifest = load_project(tmp_path)
    with pytest.raises(M2VError, match="materials.storyboard"):
        adapter.validate(root, manifest)


@pytest.mark.parametrize("field,value", [("renderer", {"kind": "code", "module": "entry"}),
                                         ("type", "financial-timeseries"), ("project", "../child")])
def test_general_rejects_code_and_embedding(tmp_path, field, value):
    data = board()
    data["scenes"][0][field] = value
    with pytest.raises(M2VError, match="未知字段"):
        explainer.validate(data, tmp_path)


def test_preparation_for_old_type_cannot_authorize_general(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch)
    legacy = {**manifest, "type": "article-narrative"}
    adapter.prepare(root, legacy)
    with pytest.raises(M2VError, match="与当前作品不匹配"):
        load_current_prepared(root, manifest)


@pytest.mark.slow
def test_general_full_preview_and_render(tmp_path, monkeypatch, chromium_ready):
    """用本地合成音频走真实浏览器、Remotion、完整预演门禁与成片验收。"""
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert main(["preview", "--project", str(root)]) == 0
    assert main(["render", "--project", str(root)]) == 0
    provenance = json.loads((root / "outputs/video.provenance.json").read_text(encoding="utf-8"))
    assert provenance["type"] == "general"
    assert provenance["compositionId"] == "ArticleExplainer"
    assert provenance["durationInFrames"] == prepared["durationInFrames"] == 42
    assert (root / "outputs/video.mp4").is_file()
