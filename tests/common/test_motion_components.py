"""共享动效组件：实现指纹、确定性闸门与 SDK 导出。"""
from __future__ import annotations

from pathlib import Path

from film_runtime.core import source_policy
from m2v.types.scene_film import code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
COMPONENTS = WEB / "src/code-scene/motion-components"
SDK = Path(__file__).resolve().parents[1] / "support/code-scene-reference.tsx"




def test_shared_components_pass_the_determinism_source_gate():
    files = sorted(COMPONENTS.glob("*.ts")) + sorted(COMPONENTS.glob("*.tsx"))
    files = [path for path in files if ".test." not in path.name]
    violations = source_policy.scan(files)
    assert not violations, [item.render(WEB) for item in violations]


def test_sdk_exports_the_shared_motion_components():
    text = SDK.read_text(encoding="utf-8")
    assert "export * from '../../web/src/code-scene/motion-components';" in text
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


def test_l1_and_l2_names_are_exported():
    l1 = (COMPONENTS / "l1.tsx").read_text(encoding="utf-8")
    l2 = (COMPONENTS / "l2.tsx").read_text(encoding="utf-8")
    for name in ("FadeIn", "SlideIn", "ZoomIn", "Blur", "Glow", "DrawLine"):
        assert f"export function {name}" in l1, name
    for name in ("RollingNumber", "Typewriter", "MarkerHighlight", "BarGrowth", "Callout"):
        assert f"export function {name}" in l2, name
