"""代码场景静态清单：生成、覆盖、跨根解析与 Git 忽略。

- 纯 tree / 纯 code / 混合分镜分别生成什么；
- 连续切换两支作品时旧引用不残留（每次整体覆盖）；
- 外部内容根的模块经 Node 生成器转义后，import 描述符由
  TypeScript 与 bundler（esbuild）解析成功；
- 生成目录与作品代码保持在 Git 忽略范围。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from a2v import scene_manifest
from conftest import SKILL_MARKER

SCENE_MODULE = "export default function Scene() { return null; }\n"


def _storyboard(renderers: list[dict | None]) -> dict:
    scenes = []
    for index, renderer in enumerate(renderers):
        scene = {
            "id": f"s{index}",
            "type": "title",
            "durationInFrames": 30,
            "data": {"text": "开场"},
            "visualIntent": {"relation": "focus", "focus": "text", "composition": "center", "density": "sparse", "tone": "neutral"},
            "motions": [],
        }
        if renderer is None:
            scene["sceneTree"] = {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text"}]}
        else:
            scene["renderer"] = renderer
        scenes.append(scene)
    return {
        "version": 2,
        "schemaVersion": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "visualDirection": {"motif": "测试", "compositionBias": "centered", "density": "sparse", "rhythm": "restrained", "avoid": []},
        "scenes": scenes,
    }


def _make_project(tmp_path: Path, slug: str) -> Path:
    marker = tmp_path / SKILL_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("# article2video skill", encoding="utf-8")
    article = tmp_path / "videos" / slug
    article.mkdir(parents=True, exist_ok=True)
    return article


def _generated(web_dir: Path) -> str:
    return (web_dir / ".gen" / "active-scenes.ts").read_text(encoding="utf-8")


@pytest.fixture
def web_dir() -> Path:
    """仓库的 web 工程（生成器在这里运行，产物落在 .gen/）。"""
    return Path(__file__).resolve().parents[1] / "web"


@pytest.fixture(autouse=True)
def restore_manifest(web_dir: Path):
    """测试前后恢复空清单：生成产物不入库，也不影响后续真实渲染。"""
    target = web_dir / ".gen" / "active-scenes.ts"
    tailwind = web_dir / ".gen" / "active-tailwind.css"
    before = target.read_text(encoding="utf-8") if target.is_file() else None
    tailwind_before = tailwind.read_text(encoding="utf-8") if tailwind.is_file() else None
    yield
    if before is None:
        subprocess.run(["node", "scripts/ensure-entry.mjs"], cwd=web_dir, check=False)
    else:
        target.write_text(before, encoding="utf-8")
    if tailwind_before is not None:
        tailwind.write_text(tailwind_before, encoding="utf-8")


class TestManifestGeneration:
    def test纯tree分镜生成空清单(self, tmp_path, web_dir):
        article = _make_project(tmp_path, "tree-only")
        storyboard = article / "storyboard.json"
        storyboard.write_text(json.dumps(_storyboard([None, None]), ensure_ascii=False), encoding="utf-8")
        scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
        text = _generated(web_dir)
        assert "ACTIVE_CODE_SCENES: Record<string, A2VCodeScene<any>> = {}" in text
        assert "import s0" not in text

    def test纯code分镜生成全部模块(self, tmp_path, web_dir):
        article = _make_project(tmp_path, "code-only")
        (article / "scenes").mkdir()
        (article / "scenes" / "intro.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        (article / "scenes" / "outro.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        storyboard = article / "storyboard.json"
        storyboard.write_text(
            json.dumps(_storyboard([{"kind": "code", "module": "intro"}, {"kind": "code", "module": "outro"}]), ensure_ascii=False),
            encoding="utf-8",
        )
        scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
        text = _generated(web_dir)
        assert "import s0 from" in text and "intro" in text
        assert "'outro': s1," in text
        # 相对描述符指向作品目录且不带扩展名（由解析器补全）
        assert "videos/code-only/scenes/intro" in text
        assert ".tsx" not in text

    def test混合分镜只含code模块(self, tmp_path, web_dir):
        article = _make_project(tmp_path, "mixed")
        (article / "scenes").mkdir()
        (article / "scenes" / "chart.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        storyboard = article / "storyboard.json"
        storyboard.write_text(
            json.dumps(_storyboard([None, {"kind": "code", "module": "chart"}, None]), ensure_ascii=False),
            encoding="utf-8",
        )
        scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
        text = _generated(web_dir)
        assert "'chart': s0," in text
        assert "import s1" not in text

    def test两幕共用模块只生成一份import(self, tmp_path, web_dir):
        article = _make_project(tmp_path, "shared")
        (article / "scenes").mkdir()
        (article / "scenes" / "intro.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        storyboard = article / "storyboard.json"
        storyboard.write_text(
            json.dumps(_storyboard([{"kind": "code", "module": "intro"}, {"kind": "code", "module": "intro"}]), ensure_ascii=False),
            encoding="utf-8",
        )
        scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
        text = _generated(web_dir)
        assert text.count("import s0 from") == 1
        assert "import s1" not in text

    def test连续切换作品不残留旧引用(self, tmp_path, web_dir):
        first = _make_project(tmp_path, "first")
        (first / "scenes").mkdir()
        (first / "scenes" / "alpha.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        second = _make_project(tmp_path, "second")
        (second / "scenes").mkdir()
        (second / "scenes" / "beta.tsx").write_text(SCENE_MODULE, encoding="utf-8")

        for article, module in ((first, "alpha"), (second, "beta")):
            storyboard = article / "storyboard.json"
            storyboard.write_text(
                json.dumps(_storyboard([{"kind": "code", "module": module}]), ensure_ascii=False),
                encoding="utf-8",
            )
            scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
            text = _generated(web_dir)
            assert f"'{module}': s0," in text

        text = _generated(web_dir)
        assert "alpha" not in text and "first" not in text
        assert "beta" in text and "second" in text

    def test缺失模块在生成前失败(self, tmp_path, web_dir):
        article = _make_project(tmp_path, "ghost")
        storyboard = article / "storyboard.json"
        storyboard.write_text(
            json.dumps(_storyboard([{"kind": "code", "module": "ghost"}]), ensure_ascii=False),
            encoding="utf-8",
        )
        with pytest.raises(Exception, match="ghost"):
            scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)


class TestCrossRootResolution:
    """外部内容根：import 描述符可被 TypeScript 与 bundler 解析。"""

    def test描述符为posix相对路径且指向真实文件(self, tmp_path, web_dir):
        root = tmp_path / "content-root"
        article = root / "videos" / "external"
        (article / "scenes").mkdir(parents=True)
        module = article / "scenes" / "chart.tsx"
        module.write_text(SCENE_MODULE, encoding="utf-8")
        generated, temp = scene_manifest.generate_to_temp(
            web_dir=web_dir, modules=[("chart", str(module.resolve()))]
        )
        text = generated.read_text(encoding="utf-8")
        assert "\\.tsx" not in text and "\\\\" not in text  # 无反斜杠
        assert ":" not in text.split("from '")[1].split("'")[0]  # 无盘符
        # 描述符从生成目录出发可解析到真实模块（扩展名由解析器补全）
        import re

        match = re.search(r"import s0 from '([^']+)'", text)
        assert match is not None
        base = temp / match.group(1)
        candidates = [base.with_suffix(ext) for ext in (".tsx", ".ts")] + [base / "index.tsx", base / "index.ts"]
        assert module.resolve() in [candidate.resolve() for candidate in candidates]

    def test生成import由bundler解析(self, tmp_path, web_dir):
        """esbuild 以 bundle 模式解析生成的清单：路径错了这里立刻失败。"""
        root = tmp_path / "content-root"
        article = root / "videos" / "external"
        (article / "scenes").mkdir(parents=True)
        module = article / "scenes" / "chart.tsx"
        module.write_text(
            "import { createSceneRandom } from '@a2v/scene';\n"
            "export default function Scene() { return null; }\n",
            encoding="utf-8",
        )
        generated, temp = scene_manifest.generate_to_temp(
            web_dir=web_dir, modules=[("chart", str(module.resolve()))]
        )
        outfile = temp / "bundle-out.js"
        # esbuild 是 vite 的传递依赖：pnpm 布局下从虚拟存储定位
        binaries = sorted(web_dir.glob("node_modules/.pnpm/esbuild@*/node_modules/esbuild/bin/esbuild"))
        if not binaries:
            pytest.skip("esbuild 不可用")
        command = [
            "node",
            str(binaries[-1]),
            str(generated),
            "--bundle",
            "--format=esm",
            "--platform=browser",
            f"--outfile={outfile}",
            f"--alias:@/code-scene={web_dir / 'src' / 'code-scene' / 'index.ts'}",
            "--external:react",
        ]
        completed = subprocess.run(command, cwd=web_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert completed.returncode == 0, completed.stderr
        assert outfile.is_file()

    @pytest.mark.slow
    def test生成import由TypeScript解析(self, tmp_path, web_dir):
        """tsc --noEmit 覆盖 .gen/：跨根 import 必须通过类型检查。"""
        # 清单生成需要作品归属：补上仓库根标记
        marker = tmp_path / SKILL_MARKER
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# article2video skill", encoding="utf-8")
        root = tmp_path / "content-root"
        article = root / "videos" / "external"
        (article / "scenes").mkdir(parents=True)
        module = article / "scenes" / "chart.tsx"
        module.write_text(SCENE_MODULE, encoding="utf-8")
        scene_manifest.generate(
            web_dir=web_dir,
            storyboard_path=_storyboard_with_module(article, module),
            content_root=root,
        )
        completed = subprocess.run(
            [shutil.which("pnpm") or "pnpm", "exec", "tsc", "--noEmit"],
            cwd=web_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr


def _storyboard_with_module(article: Path, module: Path) -> Path:
    """带一个真实模块的外部内容根分镜（供 tsc 夹具使用）。"""
    storyboard = article / "storyboard.json"
    storyboard.write_text(
        json.dumps(_storyboard([{"kind": "code", "module": module.stem}]), ensure_ascii=False),
        encoding="utf-8",
    )
    return storyboard


class TestGitIgnore:
    """任务 2.4：生成目录与作品代码产物不入库。

    本用例在**真实仓库**里检查忽略规则（`videos/` 与 `web/.gen/` 的忽略
    约定必须对仓库本身成立）。注意：绝不在仓库里创建或覆盖仓库标记等
    共享文件；作品目录直接落在已被忽略的 `videos/` 下，归属解析用真实标记。
    """

    def test生成文件被git忽略(self, web_dir):
        repo_root = web_dir.parent
        article = repo_root / "videos" / "ignored-slug-manifest-test"
        article.mkdir(parents=True, exist_ok=True)
        (article / "scenes").mkdir(exist_ok=True)
        (article / "scenes" / "intro.tsx").write_text(SCENE_MODULE, encoding="utf-8")
        storyboard = article / "storyboard.json"
        storyboard.write_text(
            json.dumps(_storyboard([{"kind": "code", "module": "intro"}]), ensure_ascii=False),
            encoding="utf-8",
        )
        try:
            scene_manifest.generate(web_dir=web_dir, storyboard_path=storyboard)
            # git status --ignored 把生成文件列为忽略，而不是未跟踪
            completed = subprocess.run(
                ["git", "status", "--ignored", "--porcelain", "web/.gen", "videos"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert completed.returncode == 0
            lines = completed.stdout.splitlines()
            # porcelain 把整个忽略目录折叠为一行：`!! web/.gen/`
            assert any(line.startswith("!! web/.gen/") for line in lines)
            assert any(line.startswith("!! videos/") for line in lines)
            tracked = subprocess.run(
                ["git", "ls-files", "web/.gen", "videos/ignored-slug-manifest-test"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert tracked.stdout.strip() == ""
        finally:
            shutil.rmtree(article, ignore_errors=True)
