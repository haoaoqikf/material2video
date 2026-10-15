"""代码场景的依赖白名单与源码安全闸门。

每条静态规则都给出**正例（必须报）与反例（必须过）**；导入图用
「入口 → 辅助模块 → 越界导入」的夹具证明传递依赖同样受检。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import m2v.core.code_gate as code_gate

GOOD_COMPONENT = "export default function Scene() { return null; }\n"


def _work(tmp_path: Path, files: dict[str, str], slug: str = "gate"):
    """搭一个带 scenes/ 的作品目录，返回 (文章目录, 入口路径)。"""
    article = tmp_path / "videos" / slug
    scenes = article / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        target = scenes / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return article, scenes / "entry.tsx"


def _scan(article: Path, entry: str = "entry.tsx") -> list[code_gate.Violation]:
    return code_gate.scan(article_dir=article, modules=[article / "scenes" / entry])


def _rules(violations: list[code_gate.Violation]) -> list[str]:
    return [v.rule for v in violations]


class TestDependencyWhitelist:
    def test白名单依赖放行(self, tmp_path):
        article, entry = _work(
            tmp_path,
            {
                "entry.tsx": (
                    "import { useState } from 'react';\n"
                    "import { createRoot } from 'react-dom/client';\n"
                    "import { useCurrentFrame } from 'remotion';\n"
                    "import { random } from '@m2v/scene';\n"
                    f"{GOOD_COMPONENT}"
                )
            },
        )
        assert _scan(article) == []

    def test非白名单包被拒并报告包名(self, tmp_path):
        article, entry = _work(tmp_path, {"entry.tsx": "import x from 'lodash';\n"})
        violations = _scan(article)
        assert any("A1" in v.rule and "lodash" in v.message for v in violations)
        assert violations[0].line == 1

    def test_remotion子包放行_任意作用域包被拒(self, tmp_path):
        article, _ = _work(tmp_path, {"entry.tsx": "import '@remotion/fonts';\nimport '@evil/pkg';\n"})
        violations = _scan(article)
        assert not any("A1" in v.rule and "@remotion/fonts" in v.message for v in violations)
        assert any("A1" in v.rule and "@evil/pkg" in v.message for v in violations)

    def test项目别名不对作品开放(self, tmp_path):
        article, _ = _work(tmp_path, {"entry.tsx": "import { GeneralVideo } from '@/compositions/GeneralVideo';\n"})
        violations = _scan(article)
        assert any("A1" in v.rule and "@m2v/scene" in v.message for v in violations)

    def testNode内置模块被拒(self, tmp_path):
        article, _ = _work(
            tmp_path,
            {"entry.tsx": "import fs from 'fs';\nimport path from 'node:path';\n"},
        )
        violations = _scan(article)
        assert sum("A2" in v.rule for v in violations) == 2

    def test_require与动态import被拒(self, tmp_path):
        article, _ = _work(
            tmp_path,
            {
                "entry.tsx": (
                    "const a = require('./helper');\n"
                    "const b = await import('./helper');\n"
                    "const c = import(moduleName);\n"
                )
            },
        )
        violations = _scan(article)
        assert len([v for v in violations if "A3" in v.rule]) == 3

    def test越界相对导入被拒_传递依赖同样受检(self, tmp_path):
        # 作品外的辅助文件：入口引用它，它再引用非白名单包——两层都要拦
        article, scenes = _work(tmp_path, {"entry.tsx": "import { x } from '../../escape';\n"})
        outside = article / "escape.ts"
        outside.write_text("import _ from 'lodash';\nexport const x = 1;\n", encoding="utf-8")
        violations = _scan(article)
        assert any("A4" in v.rule and "escape" in v.message for v in violations)

    def test场景内相对导入与assets放行(self, tmp_path):
        article, _ = _work(
            tmp_path,
            {
                "entry.tsx": (
                    "import { helper } from './helper';\n"
                    "import icon from '../assets/icon.svg';\n"
                    "import styles from './styles.css';\n"
                    f"{GOOD_COMPONENT}"
                ),
                "helper.ts": "export const helper = 1;\n",
                "styles.css": ".box { color: red; }\n",
            },
        )
        (article / "assets").mkdir(exist_ok=True)
        (article / "assets" / "icon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        assert _scan(article) == []

    def test解析不到的相对导入报错(self, tmp_path):
        article, _ = _work(tmp_path, {"entry.tsx": "import './missing';\n"})
        violations = _scan(article)
        assert any("A4" in v.rule and "missing" in v.message for v in violations)


class TestStaticRules:
    """/每条规则：正例必须报、反例必须过。"""

    def _assert_positive(self, tmp_path, body: str, rule_id: str):
        article, _ = _work(tmp_path, {"entry.tsx": body})
        violations = _scan(article)
        assert any(rule_id in v.rule for v in violations), [v.render(article) for v in violations]

    def _assert_negative(self, tmp_path, body: str, rule_id: str):
        article, _ = _work(tmp_path, {"entry.tsx": body})
        violations = _scan(article)
        assert not any(rule_id in v.rule for v in violations), [v.render(article) for v in violations]

    def test_A5动态求值(self, tmp_path):
        self._assert_positive(tmp_path, "eval('1+1');\nconst f = new Function('return 1');\n", "A5")
        self._assert_negative(tmp_path, "const add = (a: number) => a + 1;\n", "A5")

    def test_A6进程文件系统(self, tmp_path):
        self._assert_positive(tmp_path, "const home = process.env.HOME;\n", "A6")
        self._assert_negative(tmp_path, "const style = { padding: 12 };\n", "A6")

    def test_A7网络API(self, tmp_path):
        self._assert_positive(tmp_path, "const r = fetch('./data.json');\n", "A7")
        self._assert_negative(tmp_path, "const data = { value: 1 };\n", "A7")

    def test_A8外部URL(self, tmp_path):
        self._assert_positive(tmp_path, "const url = 'https://cdn.example.com/a.png';\n", "A8")
        self._assert_positive(tmp_path, "const s = <div style={{ backgroundImage: 'url(https://x.test/y.png)' }} />;\n", "A8")
        self._assert_negative(tmp_path, "const url = './local.png';\n", "A8")

    def test_A9挂钟(self, tmp_path):
        self._assert_positive(tmp_path, "const t = Date.now();\nconst u = performance.now();\nconst d = new Date();\n", "A9")
        self._assert_negative(tmp_path, "const epoch = new Date(0);\nconst iso = new Date('2024-01-01T00:00:00Z');\n", "A9")

    def test_A10系统随机(self, tmp_path):
        self._assert_positive(tmp_path, "const r = Math.random();\n", "A10")
        self._assert_negative(tmp_path, "const r = random('node');\n", "A10")

    def test_A11计时器(self, tmp_path):
        self._assert_positive(tmp_path, "setTimeout(() => {}, 100);\nsetInterval(() => {}, 100);\n", "A11")
        self._assert_negative(tmp_path, "const duration = 100;\n", "A11")

    def test_A12动画循环(self, tmp_path):
        self._assert_positive(tmp_path, "requestAnimationFrame(() => {});\n", "A12")
        self._assert_negative(tmp_path, "const frame = useCurrentFrame();\n", "A12")

    def test_A13CSS时间动画(self, tmp_path):
        article, _ = _work(
            tmp_path,
            {
                "entry.tsx": "import './styles.css';\nconst style = { transition: 'opacity 0.3s' };\n",
                "styles.css": ".box { animation: spin 1s linear infinite; }\n",
            },
        )
        violations = _scan(article)
        assert len([v for v in violations if "A13" in v.rule]) == 2

    def test_A13反例_帧驱动样式放行(self, tmp_path):
        self._assert_negative(tmp_path, "const style = { opacity: progress };\n", "A13")

    def test_A14SVG逃生口(self, tmp_path):
        article, _ = _work(tmp_path, {})
        (article / "scenes" / "icon.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'>"
            "<use href='../other.svg'/>"
            "<rect onclick='evil()' width='1' height='1'/>"
            "</svg>",
            encoding="utf-8",
        )
        violations = code_gate.scan(article_dir=article, modules=[article / "scenes" / "icon.svg"])
        assert len([v for v in violations if "A14" in v.rule]) == 2

    def test_A14反例_同文档use放行(self, tmp_path):
        article, _ = _work(tmp_path, {})
        (article / "scenes" / "icon.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'><use href='#dot'/></svg>",
            encoding="utf-8",
        )
        violations = code_gate.scan(article_dir=article, modules=[article / "scenes" / "icon.svg"])
        assert not [v for v in violations if "A14" in v.rule]

    def test_A15自建composition(self, tmp_path):
        self._assert_positive(tmp_path, "import { registerRoot } from 'remotion';\nregisterRoot(null);\n", "A15")
        self._assert_positive(tmp_path, "const el = <Composition id='X' />;\n", "A15")
        self._assert_negative(tmp_path, "const el = <div />;\n", "A15")

    def test诊断带行列(self, tmp_path):
        article, _ = _work(
            tmp_path,
            {"entry.tsx": "import react from 'react';\n\n   const x = Math.random();\n"},
        )
        violations = _scan(article)
        random_hit = next(v for v in violations if "A10" in v.rule)
        assert random_hit.line == 3
        assert random_hit.column == 14


class TestOrchestration:
    def test_check_storyboard从分镜出发(self, tmp_path):
        article = tmp_path / "videos" / "slug"
        (article / "scenes").mkdir(parents=True)
        (article / "scenes" / "bad.tsx").write_text("const x = Math.random();\n", encoding="utf-8")
        storyboard = {
            "scenes": [
                {
                    "id": "s0",
                    "renderer": {"kind": "code", "module": "bad"},
                }
            ]
        }
        violations = code_gate.check_storyboard(article_dir=article, storyboard_data=storyboard)
        assert any("A10" in v.rule for v in violations)

    def test_check_storyboard无代码场景返回空(self, tmp_path):
        violations = code_gate.check_storyboard(article_dir=tmp_path, storyboard_data={"scenes": []})
        assert violations == []
