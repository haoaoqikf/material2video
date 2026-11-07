"""通用适配器只接入 v8 全画布代码场景，不再桥接旧动画 CLI。"""
import json
import pytest
from m2v.core.errors import M2VError
from m2v.types.scene_film import adapter
from helpers.scene_film import project, fake_record, fake_tts

pytestmark = pytest.mark.media


def test_adapter_uses_v8_composition(tmp_path,monkeypatch):
    root,manifest=project(tmp_path);fake_tts(monkeypatch);fake_record(monkeypatch)
    result=adapter.prepare(root,manifest)
    assert result["compositionId"] == "ArticleExplainer"
    assert result["props"]["version"] == 8
    tracks=result["audio"]["segments"]
    assert len(tracks)==1 and (root / tracks[0]["path"]).is_file()


def test_pre_render_check_accepts_prepared_without_preview(tmp_path,monkeypatch):
    from m2v.cli import _register_builtins
    _register_builtins()
    root,manifest=project(tmp_path);fake_tts(monkeypatch);fake_record(monkeypatch)
    adapter.prepare(root,manifest)
    adapter.pre_render_check(root,manifest)


def test_old_preparation_is_rejected(tmp_path,monkeypatch):
    root,manifest=project(tmp_path);fake_tts(monkeypatch);fake_record(monkeypatch)
    result=adapter.prepare(root,manifest)
    from m2v.core.project import save_prepared
    save_prepared(root,project=manifest,composition_id="M2V",props={"version":4},width=1080,height=1920,fps=60,duration_in_frames=1200,inputs=result["inputs"])
    with pytest.raises(M2VError,match="旧文章准备"):
        adapter.explainer_render.current(root,manifest)
