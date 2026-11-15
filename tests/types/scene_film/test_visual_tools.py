"""外部表达组件与合成转场的定向集成；慢测只保留一个组合场景。"""
import json
import io
import subprocess
import shutil
import hashlib
from pathlib import Path

import pytest

from helpers.scene_film import WEB, board, scene, scene_root, scene_page, fake_record, fake_tts, project, requires_node
from m2v.core.errors import M2VError
from m2v.types.scene_film import adapter, explainer


def test_transition_registry_validation(tmp_path):
    for name in explainer.TRANSITIONS:
        data = board(scenes=[scene('a'), scene('b', transition=name)])
        explainer.validate(data, scene_root(tmp_path))
    with pytest.raises(M2VError, match='首幕必须 cut'):
        explainer.validate(board(scenes=[scene(transition='iris')]), scene_root(tmp_path))
    with pytest.raises(M2VError, match='转场仅支持'):
        explainer.validate(board(scenes=[scene('a'), scene('b', transition='unknown')]), scene_root(tmp_path))


@pytest.mark.media
def test_transition_preparation_keeps_single_frame_overlap(tmp_path, monkeypatch):
    data = board(fps=30, targetSeconds=2, scenes=[scene('a', durationFrames=30, narrationSegments=[]),
        scene('b', durationFrames=12, narrationSegments=[], transition='wipe-left', transitionFrames=1)])
    root, manifest = project(tmp_path, data)
    fake_record(monkeypatch); fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    a, b = prepared['props']['compiledScenes']
    assert prepared['durationInFrames'] == 41
    assert b['transition'] == 'wipe-left' and b['startFrame'] == a['endFrame'] - 1


@pytest.mark.slow
@requires_node
@pytest.mark.parametrize('mode', ['missing', 'corrupt'])
def test_formula_build_rejects_unrestored_fonts_without_mutating_assets(tmp_path, mode):
    source = tmp_path / 'project'
    (source / 'scenes').mkdir(parents=True)
    (source / 'scenes/main.tsx').write_text("import {MathFormula} from 'm2v/code-scene/math'; export default () => <MathFormula tex='x'/>;", encoding='utf-8')
    output = tmp_path / 'out'; output.mkdir()
    preload = tmp_path / 'fs.cjs'
    method = 'existsSync' if mode == 'missing' else 'readFileSync'
    result = 'false' if mode == 'missing' else 'Buffer.from("damaged")'
    preload.write_text(f"const fs=require('node:fs');const original=fs.{method};fs.{method}=function(file,...args){{if(String(file).includes('assets/math/KaTeX_Main-Regular.woff2')||String(file).includes('assets\\\\math\\\\KaTeX_Main-Regular.woff2'))return {result};return original.call(this,file,...args)}};", encoding='utf-8')
    font = WEB / 'src/assets/math/KaTeX_Main-Regular.woff2'
    before = hashlib.sha256(font.read_bytes()).hexdigest()
    process = subprocess.run([shutil.which('node'), '--require', str(preload), str(WEB / 'scripts/build-code-scene.mjs'),
        str(source), 'scenes/main.tsx', str(output)], cwd=WEB, capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert process.returncode and '公式字体缺失或摘要失配' in process.stderr
    assert not (output / 'scene.js').exists()
    assert hashlib.sha256(font.read_bytes()).hexdigest() == before


SOURCE = r'''
import {useEffect, useState} from 'react';
import {useSceneContext} from 'm2v/code-scene';
import {Diagram, layoutDiagram, type DiagramLayout} from 'm2v/code-scene/diagram';
import {MathFormula, ensureMathReady} from 'm2v/code-scene/math';
import {Atom} from 'm2v/code-scene/icons';
export default function Scene() {
  const {ready, elapsedSeconds} = useSceneContext();
  const [layout, setLayout] = useState<DiagramLayout | null>(null);
  useEffect(() => {
    Promise.all([layoutDiagram([{id:'a',label:'原因',width:88,height:36},
      {id:'b',label:'结果',width:88,height:36}], [{id:'ab',source:'a',target:'b'}]), ensureMathReady()])
      .then(([value]) => setLayout(value));
  }, []);
  useEffect(() => {if (layout) ready();}, [layout, ready]);
  return <div style={{width:320,height:240,background:'#101724',color:'#f4e9d8',padding:12,boxSizing:'border-box'}}>
    <Atom size={32} color="#f4cf67"/>
    <div style={{height:90}}><MathFormula tex="\frac{1}{2}+\sqrt{x^2}" fontSize={28}/></div>
    {layout && <Diagram layout={layout} progress={.4+elapsedSeconds} fontSize={18}/>}
  </div>;
}
'''


@pytest.mark.slow
def test_external_visual_tools_seek_offline(tmp_path, chromium_ready):
    with scene_page(tmp_path, SOURCE, frames=12, extra={'captureMode': 'pure-time'}) as (page, work):
        frames = {}
        for frame in [0, 5, 2, 5]:
            page.evaluate('(f) => window.__M2V_CODE__.advanceToFrame(f)', frame)
            screenshot = page.screenshot()
            if frame in frames:
                assert frames[frame] == screenshot
            frames[frame] = screenshot
        assert page.locator('.katex').count() == 1
        assert page.evaluate('document.fonts.check("16px KaTeX_Main")')
        assert page.locator('svg.lucide-atom').count() == 1
        assert page.evaluate('performance.getEntriesByType("resource").every(e => e.name.startsWith(location.origin) || e.name.startsWith("data:"))')
        page.screenshot(path=str(work / 'visual-tools.png'))
        print(f'visual proof: {work / "visual-tools.png"}')
        inputs = json.loads((work / 'inputs.json').read_text(encoding='utf-8'))
        assert any(Path(name).suffix == '.woff2' for name in inputs)


@pytest.mark.slow
def test_real_transition_composition_windows(tmp_path, chromium_ready):
    """一个浏览器检查所有转场端点、单帧与局部媒体偏移，不重复编码完整成片。"""
    from PIL import Image
    from playwright.sync_api import sync_playwright
    from film_runtime.engine.contract_page import serve_contract_page
    from m2v.production.model import ffmpeg

    Image.new('RGB', (320, 240), 'red').save(tmp_path / 'a.png')
    Image.new('RGB', (320, 240), 'blue').save(tmp_path / 'b.png')
    names = [name for name in explainer.TRANSITIONS if name != 'cut']
    def props(name, overlap=12):
        return dict(version=9, schemaVersion=9, fps=30, width=320, height=240, title='',
            durationInFrames=48-overlap,
            subtitle=dict(safeArea=dict(x=8,y=200,width=304,height=32), fontSize=14,
                          lineHeight=1.2,textColor='#ffffff',plateColor='#0b0d12'),
            subtitleCues=[dict(startFrame=12,endFrame=24,text='保留字幕')], compiledScenes=[
                dict(id='a',startFrame=0,endFrame=24,durationInFrames=24,transition='cut',transitionFrames=0,
                     mediaPath='',stillPath='/a.png'),
                dict(id='b',startFrame=24-overlap,endFrame=48-overlap,durationInFrames=24,transition=name,
                     transitionFrames=overlap,mediaPath='',stillPath='/b.png')])
    cases = [props(name) for name in names] + [props('wipe-left', 1)]
    # 原幕逐帧红色增加；只录制第6帧起的窗口，验证 Sequence 不会重复加媒体偏移。
    ffmpeg(['-f','lavfi','-i',"nullsrc=s=320x240:r=30:d=0.8,geq=r='N*8':g=0:b=0",
            '-vf','trim=start_frame=6,setpts=PTS-STARTPTS','-c:v','libx264','-pix_fmt','yuv420p',str(tmp_path/'window.mp4')])
    partial = props('crossfade')
    partial['compiledScenes'][1].pop('stillPath')
    partial['compiledScenes'][1].update(mediaPath='/window.mp4', mediaStartFrame=6, mediaDurationFrames=18)
    cases.append(partial)
    for index, case in enumerate(cases):
        (tmp_path/f'props-{index}.json').write_text(json.dumps(case), encoding='utf-8')
    with serve_contract_page(tmp_path/'props-0.json', tmp_path, WEB) as url, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width':320,'height':240})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            for index in range(len(names)):
                page.goto(url.replace('props-0.json', f'props-{index}.json'))
                page.wait_for_function('Boolean(window.__M2V__)')
                page.evaluate('window.__M2V__.ready()')
                shots = []
                for frame in [0, 17, 23, 17]:
                    page.evaluate('(f) => window.__M2V__.seekToFrame(f)', frame)
                    shots.append(page.screenshot())
                    if frame >= 12:
                        assert page.locator('[data-m2v-copy]').inner_text() == '保留字幕'
                assert shots[1] == shots[3] and shots[1] not in (shots[0], shots[2])
                assert Image.open(io.BytesIO(shots[0])).getpixel((80,80))[:3] == (255,0,0)
                assert Image.open(io.BytesIO(shots[2])).getpixel((80,80))[:3] == (0,0,255)
            page.goto(url.replace('props-0.json', f'props-{len(names)}.json'))
            page.wait_for_function('Boolean(window.__M2V__)'); page.evaluate('window.__M2V__.ready()')
            assert Image.open(io.BytesIO(page.screenshot())).getpixel((80,80))[:3] == (255,0,0)
            page.evaluate('window.__M2V__.seekToFrame(23)')
            assert Image.open(io.BytesIO(page.screenshot())).getpixel((80,80))[:3] == (0,0,255)
            page.goto(url.replace('props-0.json', f'props-{len(names)+1}.json'))
            page.wait_for_function('Boolean(window.__M2V__)'); page.evaluate('window.__M2V__.ready()')
            page.evaluate('window.__M2V__.seekToFrame(23)')
            page.wait_for_function('Array.from(document.querySelectorAll("video")).every(v => Math.abs(v.currentTime - 5/30) < .02 && !v.seeking && v.readyState >= 2)')
            red = Image.open(io.BytesIO(page.screenshot())).getpixel((80,80))[:3]
            # HTML5 解码在 PTS 边界可取前一帧；允许一个色阶（8），重加偏移则偏差48。
            assert abs(red[0] - 88) <= 8 and red[1] < 8 and red[2] < 8, red
            assert not errors, errors
        finally:
            browser.close()
