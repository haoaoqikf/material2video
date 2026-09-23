"""代码场景：renderer 判别联合、模块归属解析与校验诊断。

覆盖三组行为：

1. **结构校验**（纯 dict）：缺省/显式 tree、显式 code + module、互斥字段
   （code + sceneTree、code + motions）、无效渲染模式与非法模块标识；
2. **模块解析**（临时作品目录）：模块必须落在当前作品 ``scenes/`` 内，
   仓库内与外部内容根行为一致；缺失模块与错误导出报出精确位置；
3. **CLI JSON 快照**：``validate.py --json`` 的错误结构可直接被程序消费。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2v import code_scenes as cs
from a2v import storyboard as sb
from a2v.cli import main_validate


def _base_scene(renderer: dict | None = None) -> dict:
    """一个结构完整的最小场景；renderer 缺省按 tree 解释。"""
    scene = {
        "id": "intro",
        "type": "title",
        "durationInFrames": 30,
        "data": {"text": "开场"},
        "visualIntent": {"relation": "focus", "focus": "text", "composition": "center", "density": "sparse", "tone": "neutral", "mode": "typography", "claim": "展示开场", "showWithoutText": "单个焦点文字块", "primaryObject": "开场文字", "motionMeaning": "逐步出现"},
        "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text"}]},
        "motions": [],
        "renderer": {"kind": "tree"},
        "camera": {"shot": "medium", "composition": "center", "depth": "flat", "focus": "root", "segments": [{"phase": "establish", "kind": "hold", "focus": "root"}]},
    }
    if renderer is not None:
        scene["renderer"] = renderer
    return scene


def _storyboard(scenes: list[dict]) -> dict:
    for index, scene in enumerate(scenes):
        if index:
            scene.setdefault("transition", {"kind": "dissolve", "meaning": "切换至下一幕"})
    return {
        "version": 3,
        "schemaVersion": 3,
        "directingVersion": 1,
        "directingBrief": {"thesis": "测试命题", "audienceShift": "理解场景", "emotionalArc": ["观察", "确认"], "visualMotif": "焦点", "stylePack": "editorial", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"},
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "visualDirection": {"motif": "测试", "compositionBias": "centered", "density": "sparse", "rhythm": "restrained", "avoid": []},
        "scenes": scenes,
    }


def _errors(report: sb.Report) -> dict[str, str]:
    return {issue.path: issue.message for issue in report.errors}


class TestRendererStructure:
    def test显式tree_renderer按tree解释(self):
        report = sb.validate(_storyboard([_base_scene()]))
        assert report.ok, [i.format() for i in report.issues]

    def test拒绝缺省renderer(self):
        scene = _base_scene()
        scene.pop("renderer")
        report = sb.validate(_storyboard([scene]))
        assert "scenes[0].renderer" in _errors(report)

    def test显式tree_renderer通过(self):
        report = sb.validate(_storyboard([_base_scene({"kind": "tree"})]))
        assert report.ok, [i.format() for i in report.issues]

    def test纯code分镜通过结构校验(self):
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        report = sb.validate(_storyboard([scene]))
        assert report.ok, [i.format() for i in report.issues]

    def test混合模式通过结构校验(self):
        tree = _base_scene()
        code = _base_scene({"kind": "code", "module": "charts/bars"})
        code["id"] = "chart-scene"
        del code["sceneTree"]
        report = sb.validate(_storyboard([tree, code]))
        assert report.ok, [i.format() for i in report.issues]

    def test拒绝未知渲染模式(self):
        report = sb.validate(_storyboard([_base_scene({"kind": "canvas"})]))
        message = _errors(report).get("scenes[0].renderer.kind", "")
        assert "canvas" in message and "tree" in message and "code" in message

    def testcode与sceneTree互斥(self):
        report = sb.validate(_storyboard([_base_scene({"kind": "code", "module": "intro"})]))
        assert "scenes[0].sceneTree" in _errors(report)

    def testcode场景拒绝motions(self):
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        scene["motions"] = [{"target": "x", "recipe": "fade", "startFrame": 0}]
        report = sb.validate(_storyboard([scene]))
        assert "scenes[0].motions" in _errors(report)

    @pytest.mark.parametrize("module", ["intro.tsx", "C:/evil", "/abs", "../escape", "./here", "a/../b", ".hidden", "a\\b", ""])
    def test非法模块标识被拒(self, module: str):
        scene = _base_scene({"kind": "code", "module": module})
        del scene["sceneTree"]
        report = sb.validate(_storyboard([scene]))
        assert "scenes[0].renderer.module" in _errors(report)

    def testrenderer不支持module之外的字段(self):
        scene = _base_scene({"kind": "code", "module": "intro", "props": {}})
        del scene["sceneTree"]
        report = sb.validate(_storyboard([scene]))
        assert "scenes[0].renderer.props" in _errors(report)


class TestModuleResolution:
    def _write_module(self, article: Path, module: str, body: str | None = None) -> Path:
        scenes = article / "scenes"
        target = scenes / f"{module}.tsx"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body or "export default function Scene() { return null; }\n", encoding="utf-8")
        return target

    def test仓库内作品模块可解析(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        self._write_module(article, "intro")
        assert cs.resolve_module(article, "intro") == article / "scenes" / "intro.tsx"
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        assert cs.check(_storyboard([scene]), article) == []

    def test外部内容根作品模块可解析(self, tmp_path: Path):
        root = tmp_path / "content"
        article = root / "videos" / "slug"
        article.mkdir(parents=True)
        self._write_module(article, "nested/thing")
        scene = _base_scene({"kind": "code", "module": "nested/thing"})
        del scene["sceneTree"]
        assert cs.check(_storyboard([scene]), article) == []

    def test模块不在scenes目录时视为缺失(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        # 文件放在作品根而不是 scenes/：归属检查不允许这样引用
        (article / "intro.tsx").write_text("export default function Scene() { return null; }\n", encoding="utf-8")
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        issues = dict(cs.check(_storyboard([scene]), article))
        assert "scenes[0].renderer.module" in issues
        assert "不存在" in issues["scenes[0].renderer.module"]

    def test缺失模块报告精确路径与尝试记录(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        scene = _base_scene({"kind": "code", "module": "ghost"})
        del scene["sceneTree"]
        issues = dict(cs.check(_storyboard([scene]), article))
        assert "scenes[0].renderer.module" in issues
        assert "ghost" in issues["scenes[0].renderer.module"]

    def test符号链接逃出scenes被拒(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        outside = tmp_path / "outside.tsx"
        outside.write_text("export default function Scene() { return null; }\n", encoding="utf-8")
        scenes = article / "scenes"
        scenes.mkdir()
        link = scenes / "evil.tsx"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("此环境不支持符号链接")
        scene = _base_scene({"kind": "code", "module": "evil"})
        del scene["sceneTree"]
        issues = dict(cs.check(_storyboard([scene]), article))
        assert "scenes[0].renderer.module" in issues
        assert "scenes/" in issues["scenes[0].renderer.module"]


class TestExportContract:
    def _article_with(self, tmp_path: Path, body: str) -> Path:
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True, exist_ok=True)
        (article / "scenes").mkdir(exist_ok=True)
        (article / "scenes" / "intro.tsx").write_text(body, encoding="utf-8")
        return article

    def test缺少默认导出报出行号(self, tmp_path: Path):
        article = self._article_with(tmp_path, "export const helper = 1;\n")
        line, message = cs.check_export(article / "scenes" / "intro.tsx")
        assert line == 1
        assert "默认导出" in message

    def test具名导出指向export语句行(self, tmp_path: Path):
        body = "import React from 'react';\n\nexport function Scene() { return null; }\n"
        article = self._article_with(tmp_path, body)
        line, message = cs.check_export(article / "scenes" / "intro.tsx")
        assert line == 3
        assert "具名导出" in message

    def test默认导出通过(self, tmp_path: Path):
        article = self._article_with(tmp_path, "export default function Scene() { return null; }\n")
        assert cs.check_export(article / "scenes" / "intro.tsx") is None

    def test导出检查并入check结果(self, tmp_path: Path):
        article = self._article_with(tmp_path, "export const helper = 1;\n")
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        issues = dict(cs.check(_storyboard([scene]), article))
        assert "scenes[0].renderer.module" in issues
        assert "默认导出" in issues["scenes[0].renderer.module"]


class TestCliJsonSnapshot:
    """validate.py --json 的错误结构：程序化消费的契约快照。"""

    def _project_with_storyboard(self, tmp_path: Path, scene: dict) -> Path:
        # 路径归属依赖仓库根标记（与 conftest.make_project 同一约定）
        marker = tmp_path / ".agents" / "skills" / "article2video" / "SKILL.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# article2video skill", encoding="utf-8")
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True, exist_ok=True)
        storyboard = article / "storyboard.json"
        storyboard.write_text(json.dumps(_storyboard([scene]), ensure_ascii=False), encoding="utf-8")
        return storyboard

    def test缺失模块的json错误结构(self, tmp_path: Path, capsys):
        scene = _base_scene({"kind": "code", "module": "ghost"})
        del scene["sceneTree"]
        storyboard = self._project_with_storyboard(tmp_path, scene)
        exit_code = main_validate([str(storyboard), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert exit_code != 0
        assert payload["ok"] is False
        paths = {error["path"] for error in payload["errors"]}
        assert "scenes[0].renderer.module" in paths
        assert any("ghost" in error["message"] for error in payload["errors"])

    def test通过校验的code分镜json汇总(self, tmp_path: Path, capsys):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True, exist_ok=True)
        (article / "scenes").mkdir(exist_ok=True)
        (article / "scenes" / "intro.tsx").write_text(
            "export default function Scene() { return null; }\n", encoding="utf-8"
        )
        scene = _base_scene({"kind": "code", "module": "intro"})
        del scene["sceneTree"]
        storyboard = self._project_with_storyboard(tmp_path, scene)
        exit_code = main_validate([str(storyboard), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert exit_code == 0
        assert payload["ok"] is True
        assert payload["summary"]["sceneCount"] == 1
