"""正式暗场论证风格包：清单、组件契约、指纹与《样本》示例。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.types.general import explainer
from m2v.types.general.code_scenes import build_scene

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "styles" / "dark-proof"
EXAMPLE = PACKAGE / "examples" / "sample"
COMPONENTS = {
    "kit", "stage", "hero-number", "counter", "dot-field", "proof-chart",
    "bilingual-title", "screen-subtitle", "hand-drawn-line",
}


def test_manifest_tokens_and_no_assets():
    package = styles.load_style("dark-proof")
    manifest = package["manifest"]
    assert manifest["version"] == "1.0.0"
    assert set(package["components"]) == COMPONENTS
    assert "assets" not in manifest, "本包不登记字体或外部素材资产"
    assert "requires" not in manifest, "旁白可选，不能把 narration 锁成 none"
    tokens = package["tokens"]
    assert tokens["canvas"]["background"] == "#0A0B0D"
    assert tokens["colors"] == {
        "ink": "#0A0B0D", "ivory": "#F3EDDC", "gold": "#E6BE55",
        "ember": "#C43B2E", "muted": "#8B8981", "line": "#3A3A3C",
    }
    assert tokens["type"]["hero"] == 280
    assert tokens["layout"]["subjectTop"] == 140 and tokens["layout"]["subjectBottom"] == 940
    assert tokens["layout"]["marginX"] == 96
    assert "safeArea" not in tokens["layout"], "字幕安全区只能来自场景上下文"


def test_selection_rejects_wrong_type_and_frame():
    with pytest.raises(M2VError, match="类型"):
        styles.selected_style({"type": "financial-timeseries", "style": {"id": "dark-proof"}})
    with pytest.raises(M2VError, match="画幅"):
        styles.selected_style({"type": "general", "style": {"id": "dark-proof"}}, width=1080, height=1920)
    styles.selected_style({"type": "general", "style": {"id": "dark-proof"}}, width=1920, height=1080)


def test_narration_is_optional():
    from m2v.core.styles import check_requirements
    package = styles.load_style("dark-proof")
    check_requirements(package, has_narration=False)
    check_requirements(package, has_narration=True)


def test_components_are_frame_driven_and_self_contained():
    forbidden = ("Math.random", "Date.now", "setInterval", "setTimeout", "requestAnimationFrame", "@keyframes")
    for name, entry in styles.load_style("dark-proof")["components"].items():
        path = Path(entry)
        text = path.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for token in forbidden:
            assert token not in code, f"{name} 使用了 {token}"
        for module in re.findall(r"from\s+['\"]([^'\"]+)['\"]", code):
            assert module.startswith(("react", "m2v/", "./")), f"{name} 导入了未批准模块 {module}"


def test_package_does_not_carry_the_example():
    package = styles.load_style("dark-proof")
    texts = [Path(path).read_text(encoding="utf-8")
             for path in [*package["components"].values(), Path(package["root"]) / "tokens.json"]
             if Path(path).is_file()]
    joined = "\n".join(texts)
    for phrase in ("3 条评价", "盲人摸象", "样本越小", "18.26", "GOLD_INDEX"):
        assert phrase not in joined, f"包内组件出现示例题材：{phrase}"


def test_fingerprint_covers_every_package_file(tmp_path, monkeypatch):
    copy = tmp_path / "styles" / "dark-proof"
    shutil.copytree(PACKAGE, copy, ignore=shutil.ignore_patterns("examples"))
    monkeypatch.setattr(styles, "STYLES_ROOT", tmp_path / "styles")
    first = styles.load_style("dark-proof")["identity"]["fingerprint"]
    (copy / "GUIDE.md").write_text("changed", encoding="utf-8")
    second = styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert first != second


def test_example_changes_do_not_touch_package_fingerprint(tmp_path, monkeypatch):
    base = tmp_path / "styles"
    base.mkdir()
    shutil.copytree(PACKAGE, base / "dark-proof", ignore=shutil.ignore_patterns("examples"))
    example = base / "dark-proof" / "examples" / "sample"
    example.mkdir(parents=True)
    (example / "storyboard.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(styles, "STYLES_ROOT", base)
    before = styles.load_style("dark-proof")["identity"]["fingerprint"]
    (example / "storyboard.json").write_text('{"changed": true}', encoding="utf-8")
    (example / "extra.tsx").write_text("export default () => null;", encoding="utf-8")
    after = styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert before == after


def test_shipped_example_is_a_silent_v8_work():
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    assert project["type"] == "general"
    assert project["style"] == {"id": "dark-proof"}
    assert (project["output"]["width"], project["output"]["height"], project["output"]["fps"]) == (1920, 1080, 30)
    board = explainer.load(EXAMPLE, project)
    explainer.validate(board, EXAMPLE, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8
    assert board["targetSeconds"] == 58
    assert len(board["scenes"]) == 1
    scene = board["scenes"][0]
    assert scene["durationFrames"] == 1740
    assert scene["narrationSegments"] == [], "示例无旁白"
    subtitles = scene["content"]["props"]["screenSubtitles"]
    assert len(subtitles) >= 8
    for item in subtitles:
        lines = item["text"].split("\n")
        assert len(lines) == 2, f"屏幕字幕须为中英双语：{item['text']}"
        assert 0 <= item["startFrame"] < item["endFrame"] <= 1740
        assert lines[0].strip() and lines[1].strip()


def test_example_scene_uses_safe_area_and_has_no_reference_material():
    source = (EXAMPLE / "scenes" / "sample.tsx").read_text(encoding="utf-8")
    assert "subtitleSafeArea" in source
    assert "<ScreenSubtitle" in source and "safeArea={subtitleSafeArea}" in source
    assert "narrationSegments" not in source
    for relative in ("scenes/sample.tsx", "storyboard.json", "project.json",
                     "assets/synthesize.py", "assets/fetch.py"):
        text = (EXAMPLE / relative).read_text(encoding="utf-8")
        for token in ("refs/", "douyin", "7692873023291963558", "《重复》"):
            assert token not in text, f"{relative} 出现参考素材引用：{token}"


def test_example_math_relations_are_present():
    source = (EXAMPLE / "scenes" / "sample.tsx").read_text(encoding="utf-8")
    assert "3 / 1000 = 0.3%" in source
    assert "33 点摆动" in source
    assert "≈18×" in source
    assert "n × 4 → 误差 ÷ 2" in source
    assert "Math.sqrt(3)" in source and "Math.sqrt(1000)" in source
    assert "mean of three" in source


def test_example_media_recipe_is_complete():
    recipe = json.loads((EXAMPLE / "assets" / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["schemaVersion"] == 1
    identities = {item["id"] for item in recipe["assets"]}
    assert identities == {
        "bed", "swing", "impact", "scratch", "dissolve",
        "regress", "anchor", "formula", "finale",
    }
    for item in recipe["assets"]:
        assert item["transform"] == "generate"
        assert item["sampleRateHz"] == 24000 and item["channels"] == 1
        assert item["license"] == "CC0-1.0"
        assert re.fullmatch(r"[0-9a-f]{64}", item["expectedSha256"])


@pytest.mark.slow
def test_example_scene_builds_with_the_package(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(EXAMPLE, project)
    work = tmp_path / "work"
    work.mkdir()
    inputs = build_scene(EXAMPLE, board["scenes"][0], work)
    assert inputs["style"] == styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()
