"""二维绘制层：实现指纹、确定性闸门与真实离屏层合成。

生产链路的源码闸门只扫 Remotion 入口可达图，而该入口不引用 code-scene 目录，
所以绘制层不会自动被扫到——这里必须守住，否则「未进入生产扫描」会变成免检。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from m2v.core import source_policy
from m2v.types.scene_film import code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
PAINTER = WEB / "src/code-scene/painter"
CODE_SCENE = WEB / "src/code-scene"
SDK = CODE_SCENE / "sdk.tsx"


def painter_sources() -> list[Path]:
    return sorted(path for path in PAINTER.rglob("*")
                  if path.suffix in {".ts", ".tsx"} and path.is_file())


def test_painter_sources_exist():
    names = {path.name for path in painter_sources()}
    assert {"frame.ts", "bloom.ts", "usePainter.tsx", "index.ts"} <= names


def test_painter_is_part_of_the_implementation_fingerprint():
    """改绘制层必须让引用作品重新准备，不能静默复用旧片段。"""
    inputs = {name.replace("\\", "/") for name in code_scenes.implementation_inputs()}
    for path in painter_sources():
        relative = path.relative_to(ROOT).as_posix()
        assert relative in inputs, f"{relative} 未进入实现指纹"


def test_painter_passes_the_determinism_source_gate():
    """绘制层不得引入挂钟、隐式随机源、计时器或未适配的 CSS 动画。"""
    violations = source_policy.scan(painter_sources())
    assert not violations, [item.render(WEB) for item in violations]


@pytest.mark.slow
@pytest.mark.parametrize("density", [1, 2])
def test_offscreen_layer_composites_overlaps_once_at_capture_density(tmp_path, density):
    from playwright.sync_api import sync_playwright
    from m2v.types.scene_film import code_scenes
    from helpers.scene_film import prepare_build

    source = """
import {useEffect} from 'react';
import {painter, useSceneContext} from 'm2v/code-scene';
export default function Scene({width, height}: any) {
  const {ready} = useSceneContext();
  useEffect(() => { ready(); }, [ready]);
  return <painter.PainterCanvas width={width} height={height} bloom={0} grain={0}
    paint={p => { p.clear('#000000'); p.layer({alpha: .5}, layer => layer.layer({}, inner => {
      inner.circle(40, 50, 22, {fill: '#FF0000'});
      inner.circle(60, 50, 22, {fill: '#0000FF'});
    })); }} />;
}
"""
    root, work, result = prepare_build(tmp_path, source)
    assert result.returncode == 0, result.stderr
    config = {"width": 100, "height": 100, "captureScale": density, "fps": 30,
              "durationInFrames": 1, "props": {}, "media": {}, "segmentWindows": {},
              "subtitleSafeArea": {"x": 0, "y": 90, "width": 100, "height": 10}}
    pixels = {}
    def observe(page, _frame):
        pixels.update(page.evaluate("""() => {
          const c=document.querySelector('canvas'), ctx=c.getContext('2d'), s=Number(c.width/100);
          const px=(x,y)=>Array.from(ctx.getImageData(Math.round(x*s),Math.round(y*s),1,1).data);
          return {left:px(30,50), overlap:px(50,50), right:px(70,50), scale:s};
        }"""))
    with sync_playwright() as pw:
        code_scenes._capture(pw, root, work, config, selected_frames=[0], observe=observe)
    assert pixels["scale"] == density
    assert pixels["left"][0] == pytest.approx(128, abs=2)
    assert pixels["left"][2] == 0
    # 若两个对象各自以 0.5 alpha 画到目标画布，重叠像素会更亮；整体离屏合成应为 128。
    assert pixels["overlap"][2] == pytest.approx(128, abs=2)
    assert pixels["overlap"][0] == 0
    assert pixels["right"][2] == pytest.approx(128, abs=2)


def test_whole_code_scene_directory_passes_the_gate():
    """顺带覆盖宿主：这一目录整体不进入生产扫描，只能由测试守住。

    `sdk.tsx` 刻意重导出 `motion` 与 `gsap`——它们在录制页里由受控时钟驱动，
    不是「未适配的动画库入口」。闸门按字面量匹配，对这条重导出是误报，因此
    这里排除 SDK 本身，改由 `test_sdk_exports_the_painter_namespace` 单独核对其
    导出面。
    """
    sources = [path for path in CODE_SCENE.rglob("*")
               if path.suffix in {".ts", ".tsx"} and path.is_file()
               and path != SDK
               # 测试文件本身会写违规示例，不参与扫描。
               and not path.name.endswith(".test.ts") and not path.name.endswith(".test.tsx")]
    violations = source_policy.scan(sources)
    assert not violations, [item.render(WEB) for item in violations]


def test_gate_catches_injected_violations(tmp_path):
    """反例：闸门确实能拦下禁用写法，而不是恒过。"""
    sample = tmp_path / "bad.ts"
    sample.write_text("export const t = () => Date.now() + Math.random();\n", encoding="utf-8")
    found = {item.rule for item in source_policy.scan([sample])}
    assert {"挂钟时间", "随机数"} <= found


def test_painter_has_no_embedded_audience_copy():
    """面向观众的文案必须由作品传入，否则字体缺字检查看不到它。

    只查会被绘制成文字的实参：`text()` / `chars()` 的第一个参数。注释、抛给
    开发者的错误消息、测试示例都不上屏，不算内嵌文案。
    """
    offenders = []
    for path in painter_sources():
        if path.name.endswith(".test.ts") or path.name.endswith(".test.tsx"):
            continue
        text = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        for call in re.finditer(r"\b(?:text|chars)\(\s*(['\"`])((?:\\.|(?!\1).)*)\1", text):
            if re.search(r"[一-鿿]", call.group(2)):
                offenders.append(f"{path.name}: {call.group(2)[:40]}")
    assert not offenders, offenders


def test_sdk_exports_the_painter_namespace():
    """`Canvas` 已是 R3F 包装，绘制层必须以命名空间导出，避免同名符号相撞。"""
    assert "export * as painter from './painter';" in SDK.read_text(encoding="utf-8")
