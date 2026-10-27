"""用原生像素条纹证明 lookdev 重绘了 WebGL，而不是把视频放大。"""
import struct
import json
import subprocess

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright

from m2v.engine import lookdev
from m2v.core.errors import M2VError
from m2v.types.general import code_scenes
from _helpers import requires_node


SOURCE = """
import {Canvas, useFrame, useSceneContext} from 'm2v/code-scene';
function Stripes() {
  const {ready} = useSceneContext();
  useFrame(() => ready());
  return <mesh><planeGeometry args={[2,2]}/><shaderMaterial
    vertexShader={'void main(){gl_Position=vec4(position,1.0);}'}
    fragmentShader={'void main(){float s=mod(floor(gl_FragCoord.x),2.0);gl_FragColor=vec4(vec3(s),1.0);}'}/></mesh>;
}
export default function Scene() {
  return <Canvas dpr={1} gl={{antialias:false}}><Stripes/></Canvas>;
}
"""


@pytest.mark.slow
@requires_node
@pytest.mark.parametrize('sdk_canvas', [True, False], ids=['native-sdk', 'reject-low-resolution'])
def test_native_4k_has_independent_pixel_columns(tmp_path, sdk_canvas):
    root = tmp_path / 'project'
    (root / 'scenes').mkdir(parents=True)
    source = SOURCE if sdk_canvas else """
import {useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
export default function Scene() {
 const {ready}=useSceneContext(); useEffect(()=>{ready();},[]);
 return <canvas width={1920} height={1080} style={{width:1920,height:1080}}/>;
}
"""
    (root / 'scenes/stripes.tsx').write_text(source, encoding='utf-8')
    work = tmp_path / 'capture'
    work.mkdir()
    scene = {'id': 'stripes', 'content': {'entry': 'scenes/stripes.tsx', 'props': {}}}
    code_scenes.build_scene(root, scene, work)
    config = {'width': 1920, 'height': 1080, 'captureScale': 2, 'fps': 60,
              'durationInFrames': 4, 'props': {}, 'media': {}, 'segmentWindows': {},
              'subtitleSafeArea': {'x': 0, 'y': 900, 'width': 1920, 'height': 100}}
    with sync_playwright() as pw:
        if not sdk_canvas:
            with pytest.raises(M2VError, match='画布像素不足'):
                code_scenes._capture(pw, root, work, config, selected_frames=[2])
            assert not list(work.glob('frame-*.png'))
            return
        code_scenes._capture(pw, root, work, config, selected_frames=[2])
    frames = list(work.glob('frame-*.png'))
    assert [p.name for p in frames] == ['frame-000002.png']
    assert struct.unpack('>II', frames[0].read_bytes()[16:24]) == (3840, 2160)
    raw = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', str(frames[0]),
                          '-vf', 'crop=128:1:100:500', '-pix_fmt', 'gray', '-f', 'rawvideo', '-'],
                         check=True, capture_output=True).stdout
    # 1080p 放大只能得到成对像素或模糊条纹；原生 4K 的相邻列独立黑白交替。
    assert sum(abs(a - b) > 200 for a, b in zip(raw, raw[1:])) >= 120


def test_global_hero_selection_adds_scene_offset():
    prepared = {'durationInFrames': 3600, 'fps': 60, 'props': {'compiledScenes': [
        {'startFrame': 900, 'content': {'props': {'shots': [
            {'id': 'hero', 'tier': 'hero', 'startFrame': 60, 'endFrame': 180}]}}}]}}
    assert 1050 in lookdev.still_frames(prepared, 3)
    assert lookdev.sample_window(prepared, 20)[0] == 960


def test_selected_capture_validates_indices_before_browser(tmp_path):
    config = {'width': 1920, 'height': 1080, 'durationInFrames': 10}
    with pytest.raises(M2VError, match='关键帧索引'):
        code_scenes._capture(None, tmp_path, tmp_path, config, selected_frames=[10])


@pytest.mark.slow
@requires_node
def test_native_crossfade_and_subtitle_composite(tmp_path):
    from m2v.core import frames
    from m2v.engine import remotion
    root = tmp_path / 'project'
    (root / 'scenes').mkdir(parents=True)
    source = """import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
export default function Scene({props}: CodeSceneProps) {
 const {ready}=useSceneContext(); useEffect(()=>{ready();},[]);
 return <div style={{position:'absolute',inset:0,background:String(props.color)}}/>;
}"""
    (root / 'scenes/color.tsx').write_text(source, encoding='utf-8')
    subtitle = frames.spec(1920, 1080)['subtitle']
    scenes = [{'id': name, 'startFrame': start, 'endFrame': start + 4, 'durationInFrames': 4,
               'transitionFrames': transition, 'mediaPath': 'must-not-load.mp4',
               'segmentWindows': {}, 'content': {'entry': 'scenes/color.tsx', 'props': {'color': color}}}
              for name, start, transition, color in [('a', 0, 0, '#ff0000'), ('b', 2, 3, '#0000ff')]]
    props = {'version': 8, 'schemaVersion': 8, 'fps': 60, 'width': 1920, 'height': 1080,
             'title': '', 'subtitle': subtitle, 'durationInFrames': 6, 'compiledScenes': scenes,
             'subtitleCues': [{'text': '字幕验收', 'startFrame': 0, 'endFrame': 6}]}
    prepared = {'width': 1920, 'height': 1080, 'props': props}
    work = tmp_path / 'work'
    work.mkdir()
    captured = lookdev.native_stills(root, prepared, [3], work)
    assert set(captured) == {('a', 3), ('b', 3)}
    assert captured[('a', 3)].name == 'frame-000003.png'
    assert captured[('b', 3)].name == 'frame-000001.png'
    payload = lookdev.still_props(prepared, captured, 3, '')
    assert all('stillPath' not in scene for scene in props['compiledScenes'])
    config = work / 'props.json'
    config.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    bundle = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / 'bundle',
                             storyboard_path=config, content_root=root.parent, workspace_root=root.parent, cache=True)
    out = work / 'result.png'
    remotion.render_still(web_dir=remotion.web_dir(), bundle_dir=bundle.path, props=config,
                          out=out, frame=3, scale=2, composition_id='ArticleExplainer')
    assert struct.unpack('>II', out.read_bytes()[16:24]) == (3840, 2160)
    raw = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', str(out),
                          '-vf', 'crop=2:2:100:100', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                         check=True, capture_output=True).stdout
    assert 120 <= raw[0] <= 135 and raw[1] < 5 and 120 <= raw[2] <= 135
    # 字幕底板确实覆盖了混合背景（原生图按 2× 叠加字幕）。
    safe = subtitle['safeArea']
    x, y = int((safe['x'] + safe['width'] / 2) * 2), int((safe['y'] + safe['height'] / 2) * 2)
    pixels = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', str(out),
                             '-vf', f'crop=300:60:{x-150}:{y-30}', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                            check=True, capture_output=True).stdout
    assert sum(all(v > 220 for v in pixels[i:i+3]) for i in range(0, len(pixels), 3)) > 30
