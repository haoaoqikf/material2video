"""三个由仓库示例抽取的风格包：清单、组件契约、指纹与示例校验。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.types.general import explainer

ROOT = Path(__file__).resolve().parents[3]
STYLES = ROOT / "styles"

PACKAGES = {
    "doc-archive": {
        "components": {
            "kit", "archive-frame", "chapter-text", "signal-line", "waveform",
            "node-link", "flash-rings", "sequence-links", "credit-block", "schematic-badge",
        },
        "narration": "none",
        "background": "#070C10",
        "example": ("doc-archive", "american-science-milestones"),
    },
    "count-ledger": {
        "components": {"kit", "disc", "disc-layout", "world-camera", "number-text"},
        "narration": "none",
        "background": "#090B10",
        "example": ("count-ledger", "compound-interest"),
    },
    "deep-journey": {
        "components": {
            "kit", "space-stage", "orbit-ring", "planet-surface", "atmosphere",
            "chapter-track", "status-line", "info-panel", "subtitle-scrim", "boundary-footnote",
        },
        "narration": "any",
        "background": "#02050A",
        "example": ("deep-journey", "solar-system-journey"),
    },
}


def test_registry_lists_all_derived_packages(capsys):
    from m2v.cli import main
    assert main(["styles", "--json"]) == 0
    listed = {item["id"]: item for item in json.loads(capsys.readouterr().out)}
    for style_id in PACKAGES:
        assert style_id in listed
        assert listed[style_id]["types"] == ["general"]
        assert listed[style_id]["frames"] == [{"width": 1920, "height": 1080}]


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_manifest_tokens_and_no_assets(style_id: str):
    package = styles.load_style(style_id)
    manifest = package["manifest"]
    assert manifest["version"] == "1.0.0"
    assert set(package["components"]) == PACKAGES[style_id]["components"]
    assert "assets" not in manifest, "三个新包不登记 assets，避免被字体检查误拒"
    tokens = package["tokens"]
    assert tokens["canvas"]["background"] == PACKAGES[style_id]["background"]
    assert "safeArea" not in tokens["layout"]
    if PACKAGES[style_id]["narration"] == "none":
        assert manifest["requires"] == {"narration": "none"}
    else:
        assert "requires" not in manifest


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_selection_rejects_wrong_type_and_frame(style_id: str):
    with pytest.raises(M2VError, match="类型"):
        styles.selected_style({"type": "financial-timeseries", "style": {"id": style_id}})
    with pytest.raises(M2VError, match="画幅"):
        styles.selected_style({"type": "general", "style": {"id": style_id}}, width=1080, height=1920)
    styles.selected_style({"type": "general", "style": {"id": style_id}}, width=1920, height=1080)


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_components_are_frame_driven_and_self_contained(style_id: str):
    package = styles.load_style(style_id)
    forbidden = ("Math.random", "Date.now", "setInterval", "setTimeout", "requestAnimationFrame", "@keyframes")
    for name, entry in package["components"].items():
        path = Path(entry)
        text = path.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for token in forbidden:
            assert token not in code, f"{style_id}/{name} 使用了 {token}"
        for module in re.findall(r"from\s+['\"]([^'\"]+)['\"]", code):
            assert module.startswith(("react", "m2v/", "./")), (
                f"{style_id}/{name} 导入了未批准模块 {module}")


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_package_has_no_work_content(style_id: str):
    package = styles.load_style(style_id)
    text = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in [package["guide"], *package["components"].values(), Path(package["root"]) / "tokens.json"]
        if Path(path).is_file()
    )
    own = PACKAGES[style_id]["example"][1]
    for slug in ("american-science-milestones", "compound-interest", "solar-system-journey"):
        if slug == own:
            continue
        assert slug not in text, f"{style_id} 包内出现其他作品 slug {slug}"


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_fingerprint_covers_every_package_file(style_id: str, tmp_path, monkeypatch):
    package = styles.load_style(style_id)
    copy = tmp_path / "styles" / style_id
    shutil.copytree(package["root"], copy, ignore=shutil.ignore_patterns("examples"))
    monkeypatch.setattr(styles, "STYLES_ROOT", tmp_path / "styles")
    first = styles.load_style(style_id)["identity"]["fingerprint"]
    (copy / "GUIDE.md").write_text("changed", encoding="utf-8")
    second = styles.load_style(style_id)["identity"]["fingerprint"]
    assert first != second


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_example_changes_do_not_touch_package_fingerprint(style_id: str, tmp_path, monkeypatch):
    base = tmp_path / "styles"
    base.mkdir()
    shutil.copytree(styles.load_style(style_id)["root"], base / style_id, ignore=shutil.ignore_patterns("examples"))
    style, slug = PACKAGES[style_id]["example"]
    example = base / style / "examples" / slug
    example.mkdir(parents=True)
    (example / "storyboard.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(styles, "STYLES_ROOT", base)
    before = styles.load_style(style_id)["identity"]["fingerprint"]
    (example / "storyboard.json").write_text('{"changed": true}', encoding="utf-8")
    (example / "extra.tsx").write_text("export default () => null;", encoding="utf-8")
    after = styles.load_style(style_id)["identity"]["fingerprint"]
    assert before == after


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_narration_requirement(style_id: str):
    from m2v.core.styles import check_requirements
    package = styles.load_style(style_id)
    if PACKAGES[style_id]["narration"] == "none":
        check_requirements(package, has_narration=False)
        with pytest.raises(M2VError, match="无旁白"):
            check_requirements(package, has_narration=True)
    else:
        check_requirements(package, has_narration=False)
        check_requirements(package, has_narration=True)


@pytest.mark.parametrize("style_id", sorted(PACKAGES))
def test_shipped_example_uses_its_package(style_id: str):
    style, slug = PACKAGES[style_id]["example"]
    root = STYLES / style / "examples" / slug
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert project["type"] == "general"
    assert project["style"] == {"id": style_id}
    board = explainer.load(root, project)
    explainer.validate(board, root, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8
    assert (board["width"], board["height"]) == (1920, 1080)


def test_deep_journey_example_is_not_pure_time():
    """使用 useFrame 的 3D 组件只服务顺序录制；示例不得声明 pure-time。"""
    root = STYLES / "deep-journey" / "examples" / "solar-system-journey"
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    for scene in board["scenes"]:
        capture = scene.get("content", {}).get("props", {}).get("capture", {})
        assert capture.get("mode") != "pure-time"
