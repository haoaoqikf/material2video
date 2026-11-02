"""共享动效组件：实现指纹、确定性闸门与 SDK 导出。"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.core import source_policy
from m2v.types.general import code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
COMPONENTS = WEB / "src/code-scene/motion-components"
SDK = WEB / "src/code-scene/sdk.tsx"


def test_shared_components_are_part_of_the_implementation_fingerprint():
    inputs = {name.replace("\\", "/"): value for name, value in code_scenes.implementation_inputs().items()}
    for relative in (
        "web/src/code-scene/motion-components/index.ts",
        "web/src/code-scene/motion-components/internal.ts",
        "web/src/code-scene/motion-components/paths.ts",
        "web/src/code-scene/motion-components/styles.ts",
        "web/src/code-scene/motion-components/l1.tsx",
        "web/src/code-scene/motion-components/l2.tsx",
        "web/src/code-scene/motion-components/text.tsx",
        "web/src/code-scene/motion-components/morph.tsx",
        "web/src/code-scene/motion-components/gauge.tsx",
        "web/src/code-scene/motion-components/noise.tsx",
        "web/src/code-scene/motion-components/charts.tsx",
        "web/src/code-scene/motion-components/timeline.tsx",
        "web/src/code-scene/motion-components/pictogram.tsx",
        "web/src/code-scene/motion-components/waveform.tsx",
    ):
        assert relative in inputs, relative


def test_shared_components_pass_the_determinism_source_gate():
    files = sorted(COMPONENTS.glob("*.ts")) + sorted(COMPONENTS.glob("*.tsx"))
    files = [path for path in files if ".test." not in path.name]
    violations = source_policy.scan(files)
    assert not violations, [item.render(WEB) for item in violations]


def test_sdk_exports_the_shared_motion_components():
    text = SDK.read_text(encoding="utf-8")
    assert "export * from './motion-components';" in text
    index = (COMPONENTS / "index.ts").read_text(encoding="utf-8")
    for module in ("l1", "l2", "paths", "styles", "text", "morph", "gauge", "noise", "charts",
                   "timeline", "pictogram", "waveform"):
        assert f"export * from './{module}';" in index, module


def test_extended_components_are_exported():
    expected = {
        "text.tsx": ("AutoFitText", "TextBlock", "wrapText", "fitFontSize"),
        "morph.tsx": ("PathMorph", "MaskReveal"),
        "gauge.tsx": ("ArcGauge", "ProgressRing", "arcPath"),
        "noise.tsx": ("NoiseDrift", "noiseAt", "noiseDrift"),
        "charts.tsx": ("LinePlot", "AreaPlot", "Sparkline", "Axis"),
        "timeline.tsx": ("Timeline", "ChapterTrack"),
        "pictogram.tsx": ("Pictogram", "IconGrid"),
        "waveform.tsx": ("Waveform", "resamplePeaks"),
    }
    for filename, names in expected.items():
        source = (COMPONENTS / filename).read_text(encoding="utf-8")
        for name in names:
            assert f"export function {name}" in source, f"{filename}: {name}"


def test_new_dependencies_are_pinned_and_stay_out_of_the_approved_list():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    for name, version in (("@remotion/layout-utils", "4.0.526"), ("@remotion/noise", "4.0.526"),
                          ("d3-scale", "4.0.2"), ("d3-shape", "3.2.0")):
        assert package["dependencies"][name] == version, name
    build = (WEB / "scripts/build-code-scene.mjs").read_text(encoding="utf-8")
    approved_block = build.split("const approved = new Set([", 1)[1].split("]);", 1)[0]
    for name in ("@remotion/layout-utils", "@remotion/noise", "d3-scale", "d3-shape"):
        assert name not in approved_block, name


def test_l1_and_l2_names_are_exported():
    l1 = (COMPONENTS / "l1.tsx").read_text(encoding="utf-8")
    l2 = (COMPONENTS / "l2.tsx").read_text(encoding="utf-8")
    for name in ("FadeIn", "SlideIn", "ZoomIn", "Blur", "Glow", "DrawLine"):
        assert f"export function {name}" in l1, name
    for name in ("RollingNumber", "Typewriter", "MarkerHighlight", "BarGrowth", "Callout"):
        assert f"export function {name}" in l2, name


def test_approved_code_scene_packages_do_not_expose_raw_remotion_imports():
    """作品/风格包不能绕过 SDK 直接 import @remotion/*。"""
    build = (WEB / "scripts/build-code-scene.mjs").read_text(encoding="utf-8")
    approved_block = build.split("const approved = new Set([", 1)[1].split("]);", 1)[0]
    assert "@remotion/" not in approved_block
