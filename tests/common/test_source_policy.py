from __future__ import annotations

from pathlib import Path

import m2v.core.source_policy as source_policy


def _scan(tmp_path: Path, name: str, source: str):
    web = tmp_path
    target = web / "src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return source_policy.scan([target])


def test_rejects_animation_library_entry(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "import {motion} from 'motion/react';")
    assert found and found[0].rule == "动画库入口"


def test_rejects_infinite_animation_utility(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "export const x = 'animate-spin infinite';")
    assert any(item.rule == "无限动画工具类" for item in found)


def test_rejects_unclassified_css_motion(tmp_path):
    found = _scan(tmp_path, "bad.css", ".x { transition: all 1s; animation: x 1s; } @keyframes x {}")
    assert sum(item.rule == "未适配的 CSS 动画/过渡" for item in found) == 3


def test_allows_motion_declarations_that_turn_it_off(tmp_path):
    """「适配」本身（把动画关掉）不是违规：ECharts 适配器靠它压成帧驱动。"""
    found = _scan(
        tmp_path,
        "off.ts",
        "const option = {\n"
        "  animation: false,\n"
        "  animationDuration: 0,\n"
        "  animationDelay: 0,\n"
        "  transition: 'none',\n"
        "  transition: none,\n"
        "  animationDelayUpdate: 0,\n"
        "};",
    )
    assert not [item for item in found if item.rule == "未适配的 CSS 动画/过渡"]
    # 真正的时间动效仍然被抓：零值只对「整体关闭」成立，非零延迟/时长必须报
    found = _scan(tmp_path, "bad.css", ".x { animation-delay: 0.3s; transition: opacity 0.3s; }")
    assert sum(item.rule == "未适配的 CSS 动画/过渡" for item in found) == 2
    found = _scan(tmp_path, "ok.css", ".x { animation-delay: 0; transition-duration: 0ms; }")
    assert not [item for item in found if item.rule == "未适配的 CSS 动画/过渡"]


def test_rejects_effect_timer(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "useEffect(() => { setInterval(step, 10); }, []);")
    assert any(item.rule == "计时器" for item in found)


def _scan_pure(tmp_path: Path, name: str, source: str):
    target = tmp_path / "scenes" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return source_policy.scan_pure([target])


def test_pure_scan_rejects_self_driven_animation(tmp_path):
    assert any(item.rule == "R3F 逐帧回调" for item in _scan_pure(
        tmp_path, "bad.tsx", "useFrame(() => { ref.current.x += 1; });"))
    assert any(item.rule == "ECharts 自走动画" for item in _scan_pure(
        tmp_path, "chart.tsx", "import {Chart} from 'm2v/code-scene';"))
    assert any(item.rule == "真实日期" for item in _scan_pure(
        tmp_path, "clock.ts", "const now = new Date();"))
    assert any(item.rule == "媒体自走播放" for item in _scan_pure(
        tmp_path, "media.ts", "video.play();"))


def test_pure_scan_ignores_comments_and_allows_asset_state(tmp_path):
    source = """
/* 这里说明不要用 Math.random 或 setInterval */
import {useEffect, useRef, useState} from 'react';
const [loaded, setLoaded] = useState(false);
const canvas = useRef<HTMLCanvasElement>(null);
useEffect(() => { setLoaded(true); }, []);
// 也不要 requestAnimationFrame
"""
    assert _scan_pure(tmp_path, "good.tsx", source) == []


def test_scan_passes_on_repository_composition_sources():
    """仓库的可达源码整体通过闸门。

    第三方组件接入路径（`web/src/third-party/` 与分类表）已随场景树架构移除；
    这里同时守住「它没有被重新引入」——闸门本身不再有读分类表的分支。
    """
    root = Path(__file__).resolve().parents[2]
    web = root / "web"
    import m2v.engine.remotion as remotion

    assert not (web / "src/third-party").exists()
    assert source_policy.scan(remotion.build_inputs()) == []
