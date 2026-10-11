"""代码场景：renderer 判别联合、模块归属解析与校验诊断。

覆盖三组行为：

1. **结构校验**（纯 dict）：v4 的 ``world.renderer`` 判别联合——缺省/显式
   tree、显式 code + module、code 与全局 sceneTree 互斥、无效渲染模式与
   非法模块标识；
2. **模块解析**（临时作品目录）：模块必须落在当前作品 ``scenes/`` 内，
   仓库内与外部内容根行为一致；缺失模块与错误导出报出精确位置；
3. **CLI JSON 快照**：``validate.py --json`` 的错误结构与 v4 汇总可直接被
   程序消费。

入口只接受分镜 v4，renderer 声明在 ``world`` 上而不是幕内场景上，因此这里
一律用 ``conftest.v4_storyboard()`` 的骨架构造用例。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import a2v.core.code_scenes as cs
import a2v.types.article.storyboard_v4 as sb
from a2v.types.article.cli import main_validate
from a2v.types.article.storyboard import Report

from conftest import v4_storyboard


def _tree_storyboard() -> dict:
    """全片 tree renderer 的 v4 分镜骨架。"""
    return copy.deepcopy(v4_storyboard())


def _code_storyboard(module: str = "intro") -> dict:
    """全片 code renderer 的 v4 分镜：声明模块，且不得同时声明场景树。"""
    data = copy.deepcopy(v4_storyboard())
    del data["world"]["sceneTree"]
    data["world"]["renderer"] = {"kind": "code", "module": module}
    return data


def _errors(report: Report) -> dict[str, str]:
    return {issue.path: issue.message for issue in report.errors}


def _module_issues(issues: dict[str, str]) -> dict[str, str]:
    """模块解析类问题：恰好一条，落在全片 renderer 的 module 声明上。"""
    matched = {path: message for path, message in issues.items()
               if path == "world.renderer.module"}
    assert len(matched) == 1, issues
    return matched


class TestRendererStructure:
    """v4 只有一份全片 renderer，判别联合落在 ``world.renderer`` 上。"""

    def test显式tree_renderer按tree解释(self):
        report = sb.validate(_tree_storyboard())
        assert report.ok, [i.format() for i in report.issues]

    def test拒绝缺省renderer(self):
        data = _tree_storyboard()
        del data["world"]["renderer"]
        report = sb.validate(data)
        assert "world.renderer" in _errors(report)

    def test显式tree_renderer通过(self):
        data = _tree_storyboard()
        assert data["world"]["renderer"] == {"kind": "tree"}
        report = sb.validate(data)
        assert report.ok, [i.format() for i in report.issues]

    def test纯code分镜通过结构校验(self):
        report = sb.validate(_code_storyboard("intro"))
        assert report.ok, [i.format() for i in report.issues]

    # v3 允许逐幕混用 tree 与 code renderer；v4 全片只有一份 world.renderer，
    # 「混合模式」这个用例描述的旧行为已经不存在，故删除。

    def test拒绝未知渲染模式(self):
        data = _tree_storyboard()
        data["world"]["renderer"] = {"kind": "canvas"}
        message = _errors(sb.validate(data)).get("world.renderer", "")
        assert "tree" in message and "code" in message

    def testcode与sceneTree互斥(self):
        data = _tree_storyboard()
        data["world"]["renderer"] = {"kind": "code", "module": "intro"}
        assert "world.sceneTree" in _errors(sb.validate(data))

    # v3 的幕级 code 场景禁止 motions；v4 的 world.motions 目标是全局对象，
    # 对 code renderer 同样成立，「code 场景拒绝 motions」描述的旧行为已删除。

    @pytest.mark.parametrize("module", ["intro.tsx", "C:/evil", "/abs", "../escape", "./here", "a/../b", ".hidden", "a\\b", ""])
    def test非法模块标识被拒(self, module: str):
        report = sb.validate(_code_storyboard(module))
        assert "world.renderer.module" in _errors(report)

    def testrenderer不支持module之外的字段(self):
        data = _code_storyboard("intro")
        data["world"]["renderer"]["props"] = {}
        report = sb.validate(data)
        assert "world.renderer.props" in _errors(report)


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
        assert cs.check(_code_storyboard("intro"), article) == []

    def test外部内容根作品模块可解析(self, tmp_path: Path):
        root = tmp_path / "content"
        article = root / "videos" / "slug"
        article.mkdir(parents=True)
        self._write_module(article, "nested/thing")
        assert cs.check(_code_storyboard("nested/thing"), article) == []

    def test模块不在scenes目录时视为缺失(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        # 文件放在作品根而不是 scenes/：归属检查不允许这样引用
        (article / "intro.tsx").write_text("export default function Scene() { return null; }\n", encoding="utf-8")
        issues = _module_issues(dict(cs.check(_code_storyboard("intro"), article)))
        assert "不存在" in next(iter(issues.values()))

    def test缺失模块报告精确路径与尝试记录(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        issues = _module_issues(dict(cs.check(_code_storyboard("ghost"), article)))
        assert "ghost" in next(iter(issues.values()))

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
        issues = _module_issues(dict(cs.check(_code_storyboard("evil"), article)))
        assert "scenes/" in next(iter(issues.values()))


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
        issues = _module_issues(dict(cs.check(_code_storyboard("intro"), article)))
        assert "默认导出" in next(iter(issues.values()))


class TestCliJsonSnapshot:
    """validate.py --json 的错误结构与 v4 汇总：程序化消费的契约快照。"""

    def _project_with_storyboard(self, tmp_path: Path, data: dict) -> Path:
        # 路径归属依赖仓库根标记（与 conftest.make_project 同一约定）
        marker = tmp_path / ".agents" / "skills" / "article2video" / "SKILL.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# article2video skill", encoding="utf-8")
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True, exist_ok=True)
        storyboard = article / "storyboard.json"
        storyboard.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return storyboard

    def test缺失模块的json错误结构(self, tmp_path: Path, capsys):
        storyboard = self._project_with_storyboard(tmp_path, _code_storyboard("ghost"))
        exit_code = main_validate([str(storyboard), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert exit_code != 0
        assert payload["ok"] is False
        module_paths = {
            error["path"] for error in payload["errors"]
            if error["path"] == "world.renderer.module"
        }
        assert module_paths, payload["errors"]
        assert any("ghost" in error["message"] for error in payload["errors"])

    def test通过校验的code分镜json汇总(self, tmp_path: Path, capsys):
        storyboard = self._project_with_storyboard(tmp_path, _code_storyboard("intro"))
        article = storyboard.parent
        (article / "scenes").mkdir(exist_ok=True)
        (article / "scenes" / "intro.tsx").write_text(
            "export default function Scene() { return null; }\n", encoding="utf-8"
        )
        exit_code = main_validate([str(storyboard), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert exit_code == 0
        assert payload["ok"] is True
        # v4 的汇总按叙事阶段计数：骨架是三个阶段各 400 帧，全片 40 秒
        assert payload["summary"]["sceneCount"] == 3
        assert payload["summary"]["totalFrames"] == 1200
        assert payload["summary"]["durationSeconds"] == 40.0
