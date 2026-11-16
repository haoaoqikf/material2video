"""只采集三帧，验证无完整分镜时的真实网页、样式、资源和编码链路。"""
import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from m2v.core.delivery import outputs
REPO = Path(__file__).resolve().parents[2]
from m2v.core.project import create_project, load_project
from m2v.production import samples
from m2v.production.storage import write
from imageio_ffmpeg import read_frames


def install_node(root):
    subprocess.run('pnpm install --ignore-workspace --no-frozen-lockfile', cwd=root, shell=True,
                   check=True, capture_output=True, timeout=300)


def restore_fonts(root):
    (root / 'fonts/files').mkdir(parents=True, exist_ok=True)
    for name in ('Inter-Variable.ttf', 'NotoSansSC-Variable.ttf'):
        shutil.copy2(REPO / 'fonts/files' / name, root / 'fonts/files' / name)


@pytest.mark.media
@pytest.mark.parametrize('mode,supersample,kind', [('sequential', 1, 'motion'), ('pure-time', 1, 'motion'), ('sequential', 2, 'motion'), ('sequential', 1, 'static'), ('pure-time', 1, 'static')])
def test_native_sample_roundtrip_without_storyboard(tmp_path, chromium_ready, mode, supersample, kind):
    root = tmp_path / 'work'
    create_project(root, 'text-motion', {'storyboard': 'storyboard.json'})
    project = load_project(root)[1]
    project['output'].update(width=1920, height=1080, fps=30)
    write(root / 'project.json', project)
    restore_fonts(root)
    install_node(root)
    (root / 'storyboard.json').unlink(missing_ok=True)
    (root / 'scenes').mkdir(exist_ok=True)
    (root / 'scenes/style.css').write_text('body{background:rgb(11,22,33)}.object{width:100px;height:100px;background:rgb(90,180,210)}', encoding='utf-8')
    (root / 'scenes/shade.glsl').write_text('local shader text', encoding='utf-8')
    (root / 'scenes/blob.bin').write_bytes(b'local binary fixture')
    (root / 'scenes/main.tsx').write_text('''
import React,{useEffect} from 'react';
import {useSceneContext} from '../src/code-scene/context';
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
                               duration_seconds=.1, still_frames=[1], kind=kind)
    assert not (root / 'storyboard.json').exists()
    value, directory = samples.load(root, project, captured['id'])
    if mode == 'pure-time' and kind == 'motion':
        assert value['determinism']['probes']
    assert value['durationInFrames'] == 3
    if kind == 'motion':
        assert (directory / 'sample.mp4').stat().st_size > 100
        reader = read_frames(str(directory / 'sample.mp4'))
        assert next(reader)['size'] == (1920, 1080)
        reader.close()
    else:
        assert value['video'] is None and not list(directory.glob('*.mp4'))
        assert not (directory / 'process-request.json').exists()
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
    restore_fonts(root)
    import json
    package = json.loads((root / 'package.json').read_text(encoding='utf-8'))
    package['dependencies']['three'] = '0.186.1'
    (root / 'package.json').write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
    install_node(root)
    (root / 'storyboard.json').unlink(missing_ok=True)
    (root / 'scenes').mkdir(exist_ok=True)
    (root / 'scenes/main.tsx').write_text("""
import React,{useEffect} from 'react';
import * as THREE from 'three/webgpu';
import {useSceneContext} from '../src/code-scene/context';
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
