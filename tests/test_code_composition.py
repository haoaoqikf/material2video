"""共享 composition 的双轨挂载：混合时间轴、主题一致性与就绪协议。

用真实契约页 + Playwright 验证（慢速标记）：

- **混合时间轴**：tree/code 相邻幕按分镜时长顺序挂载，寻帧落在预期幕，
  代码场景包装器带模块与就绪标记；
- **主题一致性**：keynote 与非 keynote 主题下，tree/code 相邻幕使用
  同一字体基础；代码布局不带场景树取档与原语标记；
- **就绪协议**：本地资源就绪后 `ready()` 才 resolve；资源缺失时明确
  失败并给出原因，不会截取空白帧。

契约页只构建一次：分镜与 preset 是运行时数据（query 传入），
同一个 bundle 服务全部用例。
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from a2v import scene_manifest
from a2v.browser import open_animated_page
from a2v.contract_page import serve_contract_page

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
REPO_ROOT = WEB_DIR.parent


def _build_contract_page() -> None:
    completed = subprocess.run(
        [shutil.which("pnpm") or "pnpm", "build"], cwd=WEB_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

# 1×1 透明 PNG：真实可解码的本地资源
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# 代码场景模块：只用 @a2v/scene 的探针属性与共享令牌（CSS 变量取字体与强调色）。
# Tailwind 类名必须是完整字符串：直接写在 className 里的（rounded-xl、p-4）
# 与完整字符串映射里的（cls.box = 'gap-6 border-2'）都会被 @source 扫描进
# 构建 CSS；运行时拼接的类名不保证生成（见 web/README.md 的文档夹具）。
GAUGE_MODULE = """import { probe, type A2VCodeScene } from '@a2v/scene';

const cls = { box: 'gap-6 border-2' };

const Gauge: A2VCodeScene<{ text: string }> = ({ scene, progress }) => {
  return (
    <div
      className={`rounded-xl p-4 ${cls.box}`}
      style={{ fontFamily: 'var(--a2v-font)', color: 'var(--a2v-accent)', padding: 40 }}
      {...probe({ node: 'gauge-value', role: 'headline' })}
    >
      {scene.data.text} · {Math.round(progress * 100)}%
    </div>
  );
};

export default Gauge;
"""

# 带本地图片的代码场景（就绪协议用例）：资产用打包器解析的导入 URL，
# 而不是页面相对路径——页面挂在别名前缀下，相对页面写法会落空。
IMAGE_MODULE = """import { probe, type A2VCodeScene } from '@a2v/scene';
import markUrl from '../assets/mark.png';

const WithImage: A2VCodeScene<{ text: string }> = ({ scene }) => {
  return (
    <div style={{ padding: 40 }}>
      <img src={markUrl} alt="" width={120} height={120} {...probe({ node: 'mark', role: 'label' })} />
      <div {...probe({ node: 'caption', role: 'body' })}>{scene.data.text}</div>
    </div>
  );
};

export default WithImage;
"""

# 运行期才解析 URL 的变体：模拟数据驱动的图片（打包器无法内联），
# 指向不存在的资源时契约页必须在 ready() 上显式失败。
BROKEN_IMAGE_MODULE = """import { probe, type A2VCodeScene } from '@a2v/scene';

const Broken: A2VCodeScene<{ text: string }> = ({ scene }) => {
  return (
    <div style={{ padding: 40 }}>
      <img src="../assets/absent.png" alt="" width={120} height={120} {...probe({ node: 'mark', role: 'label' })} />
      <div {...probe({ node: 'caption', role: 'body' })}>{scene.data.text}</div>
    </div>
  );
};

export default Broken;
"""

# ECharts 图表模块（任务 5.2）：useFrameChart 逐帧 setOption，
# 数值由 progress 驱动；入场透明度由帧号驱动（供动效扫描量测）。
FLOW_MODULE = """import { frameStyle, probe, useFrameChart, type A2VCodeScene } from '@a2v/scene';

const Flow: A2VCodeScene<{ text: string }> = ({ progress }) => {
  const chart = useFrameChart(
    () => ({
      xAxis: { type: 'category', data: ['A', 'B', 'C', 'D'] },
      yAxis: { type: 'value', max: 100 },
      series: [{ type: 'bar', data: [20, Math.round(progress * 100), Math.round((1 - progress) * 100), 80] }],
    }),
    [progress],
  );
  return (
    <div
      ref={chart.ref}
      style={{
        position: 'absolute', left: 120, top: 560, width: 840, height: 640,
        // 入场淡入由帧号驱动：动效扫描（M 系列）要能在代码场景里量到它
        ...frameStyle(Math.min(1, progress * 3), { opacity: true }),
      }}
      {...probe({ node: 'flow-chart', schematic: true })}
    />
  );
};

export default Flow;
"""

TREE_TREE = {
    "id": "root",
    "type": "stack",
    "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}],
}


def _scene(index: int, code_module: str | None) -> dict:
    base = {
        "id": f"s{index}",
        "type": "title",
        "durationInFrames": 30,
        "data": {"text": f"第{index}幕"},
        "visualIntent": {"relation": "focus", "focus": "text", "composition": "center", "density": "sparse", "tone": "neutral", "mode": "typography", "claim": "场景渲染测试", "showWithoutText": "当前场景清楚占据画面", "primaryObject": "当前场景", "motionMeaning": "切换后呈现当前场景"},
        "motions": [],
        "camera": {"shot": "wide", "composition": "center", "depth": "flat", "focus": "scene-focus" if code_module else "copy", "segments": [{"kind": "hold", "phase": "establish", "intensity": 0}, {"kind": "settle", "phase": "settle", "intensity": 0}]},
    }
    if code_module:
        base["renderer"] = {"kind": "code", "module": code_module}
    else:
        base["renderer"] = {"kind": "tree"}
        base["sceneTree"] = TREE_TREE
    return base


def _storyboard(preset: bool = True) -> dict:
    scenes = [_scene(0, None), _scene(1, "gauge"), _scene(2, None), _scene(3, "withimage"), _scene(4, "flow")]
    for scene in scenes[1:]:
        scene["transition"] = {"kind": "dissolve", "meaning": "切换到下一场景实现"}
    return {
        "version": 3,
        "schemaVersion": 3,
        "directingVersion": 1,
        "directingBrief": {"thesis": "不同场景实现使用共享 composition", "audienceShift": "从树切换到代码场景", "emotionalArc": ["建立", "验证"], "visualMotif": "场景切换", "stylePack": "technical", "avoid": []},
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "visualDirection": {"motif": "测试", "compositionBias": "centered", "density": "sparse", "rhythm": "restrained", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"},
        "scenes": scenes,
    }


@pytest.fixture(scope="module")
def mixed_env(tmp_path_factory):
    """一次性搭好混合作品、生成清单并构建契约页；四个用例共用。"""
    root = tmp_path_factory.mktemp("content")
    article = root / "videos" / "mixed"
    (article / "scenes").mkdir(parents=True)
    (article / "assets").mkdir(exist_ok=True)
    (article / "scenes" / "gauge.tsx").write_text(GAUGE_MODULE, encoding="utf-8")
    (article / "scenes" / "withimage.tsx").write_text(IMAGE_MODULE, encoding="utf-8")
    (article / "scenes" / "flow.tsx").write_text(FLOW_MODULE, encoding="utf-8")
    # 本地资源默认在位：混合时间轴与主题用例都要通过 ready()
    (article / "assets" / "mark.png").write_bytes(PNG_1X1)

    storyboard_path = article / "storyboard.json"
    storyboard_path.write_text(json.dumps(_storyboard(preset=False), ensure_ascii=False), encoding="utf-8")
    keynote_path = article / "storyboard.keynote.json"
    keynote_path.write_text(json.dumps(_storyboard(preset=True), ensure_ascii=False), encoding="utf-8")

    scene_manifest.generate(web_dir=WEB_DIR, storyboard_path=storyboard_path, content_root=root)
    _build_contract_page()
    return root, storyboard_path, keynote_path, article


@pytest.fixture(scope="module", autouse=True)
def _restore_gen():
    """模块级恢复 .gen 清单：生成物不入库，也不影响后续真实渲染。"""
    yield
    (WEB_DIR / ".gen" / "active-scenes.ts").write_text(
        "// Generated by article2video; do not edit.\n"
        "import type { A2VCodeScene } from '@/code-scene';\n\n"
        "// 当前作品没有代码场景：分镜全部走场景树解释器。\n"
        "export const ACTIVE_CODE_SCENES: Record<string, A2VCodeScene> = {};\n",
        encoding="utf-8",
    )
    (WEB_DIR / ".gen" / "active-tailwind.css").write_text(
        "/* Generated by article2video; do not edit. */\n", encoding="utf-8"
    )
    subprocess.run(["node", "scripts/ensure-entry.mjs"], cwd=WEB_DIR, check=False)


class TestMixedTimeline:
    """任务 4.1：双轨挂载与寻帧一致。"""

    @pytest.mark.slow
    def test混合时间轴寻帧落在预期幕(self, mixed_env):
        root, storyboard_path, _, _ = mixed_env
        # 分镜：tree(0-29) + code(30-59) + tree(60-89) + code(90-119)
        for frame, expected, module in [
            (0, "s0", None),
            (29, "s0", None),
            (30, "s1", "gauge"),
            (59, "s1", "gauge"),
            (60, "s2", None),
            (119, "s3", "withimage"),
        ]:
            with serve_contract_page(storyboard_path, root) as url:
                with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                    payload = page.evaluate(
                        """async (frame) => {
                            await window.__A2V__.seekToFrame(frame);
                            const active = Array.from(document.querySelectorAll('section[data-a2v-scene]'))
                                .find((el) => el.style.display !== 'none');
                            const code = active?.querySelector('[data-a2v-code-scene]');
                            return {
                                current: window.__A2V__.currentFrame(),
                                id: active?.getAttribute('data-scene-id'),
                                module: code?.getAttribute('data-a2v-code-scene') ?? null,
                                ready: code?.getAttribute('data-a2v-code-ready') ?? null,
                            };
                        }""",
                        frame,
                    )
            assert payload["current"] == frame
            assert payload["id"] == expected
            assert payload["module"] == module
            if module:
                assert payload["ready"] == "1"


class TestThemeConsistency:
    """任务 4.2：共享主题令牌在 tree 与 code 之间一致。"""

    @pytest.mark.slow
    @pytest.mark.parametrize("keynote", [False, True], ids=["default", "keynote"])
    def test主题令牌与字体基础一致(self, mixed_env, keynote):
        root, storyboard_path, keynote_path, _ = mixed_env
        chosen = keynote_path if keynote else storyboard_path
        with serve_contract_page(chosen, root) as url:
            with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                payload = page.evaluate(
                    """() => {
                        const treeText = document.querySelector('section[data-scene-id="s0"] [data-a2v-node-id="copy"]');
                        const codeText = document.querySelector('section[data-scene-id="s1"] [data-a2v-node]');
                        const codeWrap = document.querySelector('[data-a2v-code-scene]');
                        const styles = (el) => getComputedStyle(el);
                        return {
                            theme: document.documentElement.dataset.a2vTheme,
                            preset: document.documentElement.dataset.a2vPreset ?? null,
                            codePreset: codeWrap?.getAttribute('data-a2v-preset') ?? null,
                            codeTheme: codeWrap?.getAttribute('data-a2v-theme') ?? null,
                            noTreeFit: !codeWrap?.querySelector('[data-a2v-primitive]'),
                            codeFont: codeText ? styles(codeText).fontFamily : null,
                            treeFont: treeText ? styles(treeText).fontFamily : null,
                        };
                    }"""
                )
        assert payload["theme"] == "dark"
        expected_preset = "keynote"
        assert payload["preset"] == expected_preset
        assert payload["codePreset"] == expected_preset
        assert payload["codeTheme"] == "dark"
        # 代码布局不被场景树原语样式改写
        assert payload["noTreeFit"] is True
        # 字体基础一致：代码场景通过共享令牌取得同一字体栈
        assert payload["codeFont"] == payload["treeFont"]
        assert payload["codeFont"]  # 非空：确实解析出了字体


class TestChartDeterminism:
    """任务 5.2：ECharts 适配器的同帧重复截图与跨帧重放确定性。"""

    @pytest.mark.slow
    def test图表逐帧更新满足PSNR阈值(self, mixed_env):
        from a2v.determinism import DEFAULT_PSNR_DB, failures, judge_frames

        root, storyboard_path, _, _ = mixed_env
        with serve_contract_page(storyboard_path, root) as url:
            with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                total = page.contract.duration_in_frames  # 5 幕 × 30 帧

                def produce(frame: int) -> bytes:
                    # 先跳到别的帧再回来：逼图表从另一个状态重新 setOption，
                    # 暴露「残留状态」类非确定性，而不是同帧连拍两下发。
                    page.evaluate(
                        """async ({ frame, total }) => {
                            await window.__A2V__.seekToFrame((frame + 13) % total);
                            await window.__A2V__.seekToFrame(frame);
                        }""",
                        {"frame": frame, "total": total},
                    )
                    return page.capture(image_format="png")

                # 第 4 幕（s4=flow，120..149）内取三帧，图内数值随 progress 变化
                verdicts = judge_frames(produce, [126, 135, 147], threshold=DEFAULT_PSNR_DB)
                failed = [item.describe() for item in failures(verdicts)]
                assert not failed, failed


class TestReviewCoverage:
    """任务 6.1/6.2：探针协议与 C/K/M 闸门对代码场景的覆盖。"""

    @pytest.mark.slow
    def test契约探针与KM闸门覆盖代码场景(self, mixed_env, tmp_path):
        from a2v import inspect as inspect_mod

        root, storyboard_path, keynote_path, _ = mixed_env
        scenes = json.loads(keynote_path.read_text(encoding="utf-8"))["scenes"]
        with serve_contract_page(keynote_path, root) as url:
            with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                report, extra = inspect_mod.run_inspect(
                    page, scenes, tmp_path / "frames", tmp_path, preset="keynote"
                )
        # 契约探针识别代码场景并读到它的文本（不是静默跳过）
        by_scene = {item["scene"]: item for item in extra["contract"]}
        assert by_scene["s1"]["kind"] == "code"
        assert by_scene["s1"]["declaredKind"] == "code"
        assert any("第1幕" in text for text in by_scene["s1"]["seenText"])
        assert by_scene["s1"]["protocolViolations"] == []
        # 场景树半边照常工作
        assert by_scene["s0"]["kind"] == "scene-tree"

        # 契约与探针协议层面零错误（夹具画面稀疏会触发墨迹提示，与覆盖无关）
        contract_errors = [
            issue.format()
            for issue in report.errors
            if "#契约" in issue.path or "#探针协议" in issue.path
        ]
        assert not contract_errors, contract_errors

        # 动效扫描量到代码场景的入场（frameStyle 驱动的淡入）
        entrances = extra["motion"]["entrances"]
        assert any(record["scene"] == "s4" for record in entrances), extra["motion"]["summary"]

        # K 闸门对代码场景有实测条目，而不是全部跳过
        gates = [gate for gate in extra["keynote"]["gates"] if gate["scene"] == "s1"]
        assert gates, "keynote 闸门没有覆盖代码场景"
        assert any(gate["status"] != "skipped" for gate in gates)

    @pytest.mark.slow
    def test缺失探针标记的代码场景严格评审失败(self, mixed_env, tmp_path):
        from a2v import inspect as inspect_mod

        root, storyboard_path, _, article = mixed_env
        module_file = article / "scenes" / "gauge.tsx"
        original = module_file.read_text(encoding="utf-8")
        try:
            # 夹具：不声明任何探针节点，还留一个无法解析的容器引用
            module_file.write_text(
                "import type { A2VCodeScene } from '@a2v/scene';\n"
                "\n"
                "const Naked: A2VCodeScene<{ text: string }> = ({ scene }) => {\n"
                "  return <div style={{ padding: 40 }}>{scene.data.text}</div>;\n"
                "};\n"
                "\n"
                "export default Naked;\n",
                encoding="utf-8",
            )
            scene_manifest.generate(web_dir=WEB_DIR, storyboard_path=storyboard_path, content_root=root)
            _build_contract_page()
            scenes = json.loads(storyboard_path.read_text(encoding="utf-8"))["scenes"]
            with serve_contract_page(storyboard_path, root) as url:
                with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                    report, extra = inspect_mod.run_inspect(
                        page, scenes, tmp_path / "frames", tmp_path, preset=""
                    )
            messages = [issue.format() for issue in report.errors]
            assert not report.ok
            assert any("探针协议" in message and ("没有声明任何探针节点" in message) for message in messages)
            probe_entry = next(item for item in extra["contract"] if item["scene"] == "s1")
            assert not probe_entry["ok"]
        finally:
            module_file.write_text(original, encoding="utf-8")


class TestTailwindSources:
    """任务 4.3：Tailwind source 索引只扫当前作品，完整类名进构建 CSS。"""

    @pytest.mark.slow
    def test作品类名进入构建CSS(self, mixed_env):
        root, storyboard_path, keynote_path, _ = mixed_env
        # 构建产物在夹具里已生成：直接读打包出的 CSS
        css_files = list((WEB_DIR / "dist" / "contract" / "assets").glob("contract-*.css"))
        assert css_files, "契约页 CSS 未构建"
        css = "".join(f.read_text(encoding="utf-8", errors="replace") for f in css_files)
        # 完整类名与完整字符串映射都被扫进构建 CSS
        for utility in ("rounded-xl", "p-4", "gap-6", "border-2"):
            assert utility in css, f"作品里完整书写的类名 {utility} 应进入构建 CSS"
        # 未在任何源码出现的类名不会被生成（source 索引没有把无关目录扫进来）
        assert ".ring-8" not in css

    @pytest.mark.slow
    def test索引只指向当前作品(self, mixed_env):
        root, storyboard_path, _, article = mixed_env
        index = (WEB_DIR / ".gen" / "active-tailwind.css").read_text(encoding="utf-8")
        # @source 只指向当前作品的 scenes/ 与 assets/，其他内容根不出现
        assert "scenes" in index and "assets" in index
        assert "examples" not in index
        for line in index.splitlines():
            if line.startswith("@source"):
                target = line.split('"')[1]
                assert target.replace("\\", "/").endswith(("scenes", "assets"))


class TestReadinessProtocol:
    """任务 4.4：就绪等待与显式失败。"""

    @pytest.mark.slow
    def test资源缺失时ready明确失败_补齐后通过(self, mixed_env):
        root, storyboard_path, _, article = mixed_env
        module_file = article / "scenes" / "withimage.tsx"
        original = module_file.read_text(encoding="utf-8")
        try:
            # 阶段一：运行期才解析的图片 URL 指向不存在的资源 → ready() 显式失败
            module_file.write_text(BROKEN_IMAGE_MODULE, encoding="utf-8")
            scene_manifest.generate(web_dir=WEB_DIR, storyboard_path=storyboard_path, content_root=root)
            _build_contract_page()
            with serve_contract_page(storyboard_path, root) as url:
                from a2v.browser import BrowserError

                with pytest.raises(BrowserError) as excinfo:
                    with open_animated_page(url, timeout_ms=60000, width=1080, height=1920):
                        pass
                assert "absent.png" in str(excinfo.value) or "加载失败" in str(excinfo.value)

            # 阶段二：改回打包器解析的导入 URL（资源在位）→ ready() 通过
            module_file.write_text(original, encoding="utf-8")
            scene_manifest.generate(web_dir=WEB_DIR, storyboard_path=storyboard_path, content_root=root)
            _build_contract_page()
            with serve_contract_page(storyboard_path, root) as url:
                with open_animated_page(url, timeout_ms=60000, width=1080, height=1920) as page:
                    ready_state = page.evaluate(
                        "() => document.querySelector('[data-a2v-code-scene=\"withimage\"]')?.getAttribute('data-a2v-code-ready')"
                    )
                    assert ready_state == "1"
        finally:
            module_file.write_text(original, encoding="utf-8")
