"""代码场景：模块归属解析、导出契约与校验诊断。

覆盖两组行为：

1. **模块解析**（临时作品目录）：模块必须落在当前作品 ``scenes/`` 内，
   仓库内与外部内容根行为一致；缺失模块、越界解析与错误导出报出精确位置；
2. **导出契约**（纯文本）：只认 ``export default`` 与 ``export { x as default }``，
   失败时报出源码行号。

结构校验（renderer 判别联合、互斥字段）在通用视频材料的校验里完成，
``code_scenes`` 只做需要文件系统与作品归属的部分。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import m2v.core.code_scenes as cs


def _plan(module: str = "intro") -> dict:
    """通用视频材料骨架：幕级 renderer 声明代码场景。"""
    return {"scenes": [{"id": "s0", "renderer": {"kind": "code", "module": module}}]}


def _module_issues(issues: list[tuple[str, str]]) -> dict[str, str]:
    """模块解析类问题：恰好一条，落在幕的 renderer.module 声明上。"""
    matched = {path: message for path, message in issues if path == "scenes[0].renderer.module"}
    assert len(matched) == 1, issues
    return matched


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
        assert cs.check(_plan("intro"), article) == []

    def test外部内容根作品模块可解析(self, tmp_path: Path):
        root = tmp_path / "content"
        article = root / "videos" / "slug"
        article.mkdir(parents=True)
        self._write_module(article, "nested/thing")
        assert cs.check(_plan("nested/thing"), article) == []

    def test模块不在scenes目录时视为缺失(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        # 文件放在作品根而不是 scenes/：归属检查不允许这样引用
        (article / "intro.tsx").write_text("export default function Scene() { return null; }\n", encoding="utf-8")
        issues = _module_issues(cs.check(_plan("intro"), article))
        assert "不存在" in next(iter(issues.values()))

    def test缺失模块报告精确路径与尝试记录(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        issues = _module_issues(cs.check(_plan("ghost"), article))
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
        issues = _module_issues(cs.check(_plan("evil"), article))
        assert "scenes/" in next(iter(issues.values()))

    def test语法非法的标识不在这里重复报(self, tmp_path: Path):
        article = tmp_path / "videos" / "slug"
        article.mkdir(parents=True)
        # 结构校验负责报语法；这里只处理「语法合法但落不了地」的情况
        assert cs.check(_plan("../escape"), article) == []

    def test遍历只产出声明了code的幕(self):
        plan = {
            "scenes": [
                {"id": "s0", "renderer": {"kind": "code", "module": "intro"}},
                {"id": "s1", "renderer": {"kind": "tree"}},
                {"id": "s2"},
            ]
        }
        assert [(path, module) for path, _scene, module in cs.iter_code_scenes(plan)] == [
            ("scenes[0]", "intro")
        ]


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
        issues = _module_issues(cs.check(_plan("intro"), article))
        assert "默认导出" in next(iter(issues.values()))

    @pytest.mark.parametrize(
        "module",
        ["intro.tsx", "C:/evil", "/abs", "../escape", "./here", "a/../b", ".hidden", "a\\b", ""],
    )
    def test非法模块标识被语法检查拒绝(self, module: str):
        assert cs.validate_module_id(module) is not None
