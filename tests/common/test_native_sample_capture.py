"""只采集三帧，验证无完整分镜时的真实网页、样式、资源和编码链路。"""
import io
import os

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from m2v.core.delivery import outputs
from m2v.core.project import create_project, load_project
from m2v.production import samples
from m2v.production.storage import write
from m2v.types.scene_film import code_scenes
from imageio_ffmpeg import read_frames


@pytest.mark.media
@pytest.mark.parametrize('mode,supersample', [('sequential', 1), ('pure-time', 1), ('sequential', 2)])
def test_native_sample_roundtrip_without_storyboard(tmp_path, chromium_ready, mode, supersample):
    root = tmp_path / 'work'
    create_project(root, 'text-motion', {'storyboard': 'storyboard.json'})
    project = load_project(root)[1]
    project['output'].update(width=1920, height=1080, fps=30)
    write(root / 'project.json', project)
    (root / 'scenes').mkdir()
    (root / 'scenes/style.css').write_text('body{background:rgb(11,22,33)}.object{width:100px;height:100px;background:rgb(90,180,210)}', encoding='utf-8')
    (root / 'scenes/shade.glsl').write_text('local shader text', encoding='utf-8')
    (root / 'scenes/blob.bin').write_bytes(b'local binary fixture')
    (root / 'scenes/main.tsx').write_text('''
import React,{useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
import './style.css';
import shader from './shade.glsl';
import binary from './blob.bin';
export default function Scene(){
 const {ready,elapsedSeconds}=useSceneContext();useEffect(()=>{void fetch(binary).then(r=>{if(!r.ok)throw Error('binary missing');return r.arrayBuffer();}).then(()=>ready());},[ready]);
 return <div className="object" data-shader={shader} data-binary={binary}
 style={{transform:`translateX(${elapsedSeconds*300}px)`}}/>;
}
''', encoding='utf-8')
    props = {'capture': {'mode': mode}}
    if supersample > 1:
        props.update(look={'motion': {'supersample': supersample, 'subframes': 2}},
                     shots=[{'tier': 'hero', 'startFrame': 0, 'endFrame': 2}])
    captured = samples.capture(root, project, entry='scenes/main.tsx', props=props,
                               duration_seconds=.1, still_frames=[1])
    assert not (root / 'storyboard.json').exists()
    value, directory = samples.load(root, project, captured['id'])
    if mode == 'pure-time':
        assert value['determinism']['probes']
    assert value['durationInFrames'] == 3 and (directory / 'sample.mp4').stat().st_size > 100
    reader = read_frames(str(directory / 'sample.mp4'))
    assert next(reader)['size'] == (1920, 1080)
    reader.close()
    assert (directory / 'web/scene.css').is_file()
    assert any(path.suffix == '.bin' for path in (directory / 'web').iterdir())
    with samples.server(root, project, captured['id']) as server, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1138}, device_scale_factor=1)
        page.goto(server.base_url + '/index.html')
        page.locator('#frame:enabled').wait_for()
        page.locator('#frame').fill('1')
        page.locator('#frame').press('Tab')
        page.wait_for_function("document.getElementById('status').textContent.startsWith('1 /')")
        scene = page.frames[1]
        assert scene.locator('.object').get_attribute('data-shader') == 'local shader text'
        actual = Image.open(io.BytesIO(scene.locator('body').screenshot())).convert('RGB')
        expected = Image.open(directory / value['stills'][0]['path']).convert('RGB')
        assert actual.size == expected.size
        if supersample == 1:
            assert ImageChops.difference(actual, expected).getbbox() is None
        page.locator('#reset').click()
        page.wait_for_function("document.getElementById('status').textContent.startsWith('0 /')")
        browser.close()
    if supersample == 1:
        # 正式顺序缺口与pure并行worker也必须复制CSS和binary，避免只修样品路径。
        scene = {'id': 'sample', 'durationInFrames': 3, 'startFrame': 0, 'endFrame': 3,
                 'segmentWindows': {}, 'content': {'entry': 'scenes/main.tsx', 'props': props}}
        frame = {'width': 320, 'height': 240, 'subtitle': {'safeArea': {'x': 0, 'y': 200, 'width': 320, 'height': 40}}}
        clip = code_scenes.record(root, scene, {}, frame=frame, media={}, media_digest='empty',
                                 fps=30, jobs=2 if mode == 'pure-time' else 1)
        reader = read_frames(str(root / clip))
        assert next(reader)['size'] == (320, 240)
        image = Image.frombytes('RGB', (320, 240), next(reader))
        assert all(abs(a-b) < 10 for a, b in zip(image.getpixel((30, 30)), (90, 180, 210)))
        reader.close()


@pytest.mark.media
@pytest.mark.skipif(os.name != 'nt', reason='Windows DXC浏览器包回归')
def test_webgpu_preparation_uses_a_browser_with_working_device(tmp_path, chromium_ready):
    """完整包可创建设备时，正式采集不能退回缺DXC的shell。"""
    from m2v.engine.http_server import LocalServer
    probe = tmp_path / 'probe'
    probe.mkdir()
    (probe / 'index.html').write_text('<!doctype html><title>device probe</title>', encoding='utf-8')
    with LocalServer(probe) as server, sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chromium', headless=True)
        page = browser.new_page()
        page.goto(server.base_url + '/index.html')
        supported = page.evaluate('async () => {try {const adapter=await navigator.gpu?.requestAdapter();if(!adapter)return false;const device=await adapter.requestDevice();device.destroy();return true;}catch{return false;}}')
        browser.close()
    if not supported:
        pytest.skip('当前完整Chromium也没有可用WebGPU设备')
    root = tmp_path / 'gpu-work'
    create_project(root, 'text-motion', {'storyboard': 'storyboard.json'})
    project = load_project(root)[1]
    (root / 'scenes').mkdir()
    (root / 'scenes/main.tsx').write_text("""
import React,{useEffect} from 'react';
import * as THREE from 'three/webgpu';
import {useSceneContext} from 'm2v/code-scene';
export default function Scene(){
 const {ready}=useSceneContext();
 useEffect(()=>{let renderer;
  async function init(){
   renderer=new THREE.WebGPURenderer();await renderer.init();
   if(!renderer.backend.isWebGPUBackend)throw Error('WebGPU device unavailable in capture browser');
   renderer.dispose();ready();
  }
  void init();
 },[]);
 return <div style={{width:1920,height:1080,background:'#123456'}}/>;
}
""", encoding='utf-8')
    result = samples.capture(root, project, entry='scenes/main.tsx', props={}, duration_seconds=.067, still_frames=[0])
    value, directory = samples.load(root, project, result['id'])
    assert value['durationInFrames'] == 2
    assert Image.open(directory / 'still-000000.png').convert('RGB').getpixel((100, 100)) == (18, 52, 86)
