"""作品字幕字号的配置边界、版本绑定及实际浏览器样式。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import create_project, file_inputs, load_current_prepared, load_project, save_prepared
from m2v.types.scene_film import adapter
from film_runtime.core.errors import VideoError
from film_runtime.types.scene_film import explainer_prepare, explainer_render
from helpers.scene_film import fake_record, fake_tts, project

# 这些用例需要恢复不入库的字体或示例媒体，默认排除；本地用 --full 运行。
pytestmark = pytest.mark.restored



@pytest.mark.parametrize("subtitle", [
    None, True, [], {}, {"fontSize": True}, {"fontSize": False},
    {"fontSize": 52.0}, {"fontSize": "52"}, {"fontSize": None},
    {"fontSize": 23}, {"fontSize": 57}, {"fontSize": 52, "lineHeight": 1.5},
    {"fontSize": 52, "enabled": False},
])
def test_invalid_subtitle_configuration_fails_before_prepare(tmp_path, subtitle):
    path = create_project(tmp_path, "text-motion", {"storyboard": "storyboard.json"},
                          output={"subtitle": subtitle})
    manifest = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(M2VError, match=r"output\.subtitle"):
        load_project(tmp_path)
    # 直接调用适配器也必须先拒绝，不能等到构建或 TTS 才失败。
    for operation in (adapter.validate, adapter.prepare):
        with pytest.raises(M2VError, match=r"output\.subtitle"):
            operation(tmp_path, manifest)


@pytest.mark.parametrize("font_size", [24, 52, 56])
def test_valid_subtitle_font_size(tmp_path, font_size):
    create_project(tmp_path, "text-motion", {"storyboard": "storyboard.json"},
                   output={"subtitle": {"fontSize": font_size}})
    assert load_project(tmp_path)[1]["output"]["subtitle"] == {"fontSize": font_size}


@pytest.mark.parametrize("kind", ["text-motion", "data-evolution", "principle-metaphor", "spatial-3d", "documentary-edit"])
def test_all_five_types_accept_subtitle_configuration(tmp_path, kind):
    create_project(tmp_path, kind, {"storyboard": "storyboard.json"}, output={"subtitle": {"fontSize": 52}})
    assert load_project(tmp_path)[1]["output"]["subtitle"] == {"fontSize": 52}


@pytest.mark.parametrize("before,after", [(None, 52), (40, 52), (52, None)])
def test_subtitle_configuration_change_invalidates_prepared(tmp_path, before, after):
    root, manifest = project(tmp_path)
    if before is not None:
        manifest["output"]["subtitle"] = {"fontSize": before}
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    save_prepared(root, project=manifest, composition_id="SceneFilm", props={},
                  width=1920, height=1080, fps=60, duration_in_frames=60, inputs=file_inputs(root, manifest))
    load_current_prepared(root, manifest)
    if after is None:
        manifest["output"].pop("subtitle")
    else:
        manifest["output"]["subtitle"] = {"fontSize": after}
    with pytest.raises(M2VError, match="作品描述已变化.*重新 prepare"):
        load_current_prepared(root, manifest)


@pytest.mark.slow
def test_browser_uses_prepared_subtitle_size_and_rejects_drift(tmp_path, monkeypatch, chromium_ready):
    root, manifest = project(tmp_path)
    manifest["output"]["subtitle"] = {"fontSize": 52}
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    prepared = explainer_prepare.prepare(root, manifest)
    # 量测对照准备字号而非画幅默认40；实际DOM必须为52才能通过。
    assert explainer_render.layout_check(root, prepared)["status"] == "pass"
    monkeypatch.setattr(explainer_render, "MEASURE_BODY", explainer_render.MEASURE_BODY.replace(
        "const problems = [];",
        "const problems = []; document.querySelector('[data-m2v-subtitle]').style.fontSize = '40px';"))
    with pytest.raises(VideoError, match="字幕字号不符"):
        explainer_render.layout_check(root, prepared)
