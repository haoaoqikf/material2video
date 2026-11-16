"""真实浏览器验证采集时间、动画库及三维绘制，不以帧率元数据代替运动验收。"""
from __future__ import annotations


import pytest

from film_runtime.types.scene_film import code_scenes
from helpers.scene_film import WEB, scene_page, prepare_build, requires_node


MOTION_SCENE = """
import {useEffect, useRef} from 'react';
import {motion, gsap, Canvas, useFrame, useSceneContext} from 'm2v/code-scene';
function Body({seconds}) {
  const ref = useRef();
  const {ready} = useSceneContext();
  const didReady = useRef(false);
  useFrame(() => {ref.current.position.x = seconds; window.__threeTime = ref.current.position.x;
    if (!didReady.current) {didReady.current = true; ready();}
  });
  return <mesh ref={ref}><boxGeometry/><meshBasicMaterial/></mesh>;
}
export default function Demo() {
  const {ready, running, elapsedSeconds} = useSceneContext();
  const target = useRef();
  useEffect(() => {
    if (running) {const tween = gsap.to(target.current, {x: 120, duration: 1, ease: 'none'}); return () => tween.kill();}
  }, [running]);
  return <div>
    <div id="position" style={{transform: `translateX(${elapsedSeconds * 120}px)`}}>{elapsedSeconds}</div>
    <div id="gsap" ref={target}/>
    <motion.div id="motion" initial={{opacity: 0}} animate={{opacity: running ? 1 : 0}}
      transition={{duration: 1, ease: 'linear'}}/>
    <style>{'@keyframes slide {from {transform:translateX(0px)} to {transform:translateX(120px)}}'}</style>
    <div id="css" style={{animation: running ? 'slide 1s linear both' : 'none'}}/>
    <Canvas style={{width:100,height:100}}><Body seconds={elapsedSeconds}/></Canvas>
  </div>;
}
"""


@pytest.mark.slow
@requires_node
def test_fixed_frames_sync_dom_three_and_animation_libraries(tmp_path, chromium_ready):
    with scene_page(tmp_path, MOTION_SCENE) as (page, _):
        origin = page.evaluate('performance.now()')
        for frame in range(61):
            page.evaluate('n => window.__M2V_CODE__.advanceToFrame(n)', frame)
            observed = page.evaluate("""() => ({
              seconds: Number(document.querySelector('#position').textContent),
              three: window.__threeTime,
              x: new DOMMatrix(getComputedStyle(document.querySelector('#position')).transform).m41,
              gsap: new DOMMatrix(getComputedStyle(document.querySelector('#gsap')).transform).m41,
              opacity: Number(getComputedStyle(document.querySelector('#motion')).opacity),
              css: new DOMMatrix(getComputedStyle(document.querySelector('#css')).transform).m41,
              time: performance.now()
            })""")
            assert observed['seconds'] == pytest.approx(frame / 60)
            assert observed['three'] == pytest.approx(frame / 60)
            assert observed['x'] == pytest.approx(frame * 2, abs=.001)
            assert observed['time'] == pytest.approx(origin + frame * 1000 / 60)
            assert observed['gsap'] == pytest.approx(frame * 2, abs=2.1)
            assert observed['opacity'] == pytest.approx(frame / 60, abs=.025)
            assert observed['css'] == pytest.approx(frame * 2, abs=2.1)
            if frame == 30:
                before = page.screenshot()
                page.wait_for_timeout(180)
                assert page.evaluate('performance.now()') == observed['time']
                assert page.screenshot() == before, '慢截图不能推进动画'
        with pytest.raises(Exception, match='连续帧号'):
            page.evaluate('window.__M2V_CODE__.advanceToFrame(60)')
        with pytest.raises(Exception, match='连续帧号'):
            page.evaluate('window.__M2V_CODE__.advanceToFrame(62)')
        with pytest.raises(Exception, match='绘制超时'):
            page.evaluate('window.__M2V_CAPTURE_CLOCK__.deadline(new Promise(() => {}), 20)')


def test_encode_rejects_missing_frames(tmp_path):
    with pytest.raises(Exception, match='采集帧缺失'):
        code_scenes._encode(tmp_path, tmp_path / 'clip.mp4', 2, 320, 240)


@pytest.mark.slow
def test_capture_waits_for_video_inserted_at_a_cut(tmp_path, chromium_ready):
    import base64
    import subprocess

    from imageio_ffmpeg import get_ffmpeg_exe
    from playwright.sync_api import sync_playwright

    clip = tmp_path / 'cut.mp4'
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi', '-i',
                    'color=red:size=32x32:rate=30:duration=0.5', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    str(clip)], check=True, capture_output=True)
    source = 'data:video/mp4;base64,' + base64.b64encode(clip.read_bytes()).decode('ascii')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(path=str(WEB / 'src/code-scene/capture-clock.js'))
        page.goto('about:blank')
        state = page.evaluate('''async src => {
            const clock = window.__M2V_CAPTURE_CLOCK__;
            clock.begin(0);
            clock.setTime(100);
            const video = document.createElement('video');
            video.preload = 'auto';
            video.src = src;
            document.body.append(video);
            const before = video.readyState;
            await clock.deadline(clock.flush(), 5000);
            return {before, after: video.readyState, time: performance.now()};
        }''', source)
        assert state['before'] < 2
        assert state['after'] >= 2
        assert state['time'] == 100
        with pytest.raises(Exception, match='视频资源加载失败'):
            page.evaluate('''async () => {
                const video = document.createElement('video');
                video.src = 'data:video/mp4;base64,AA==';
                document.body.replaceChildren(video);
                const clock = window.__M2V_CAPTURE_CLOCK__;
                await clock.deadline(clock.flush(), 5000);
            }''')
        browser.close()


@pytest.mark.slow
@requires_node
def test_global_time_uses_scene_start_frame(tmp_path, chromium_ready):
    source = """
import {useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
export default function Demo() {
  const clock = useSceneContext();
  useEffect(() => {clock.ready();}, []);
  return <div id="state" data-global-frame={clock.globalFrame}
    data-global-seconds={clock.globalSeconds} data-local={clock.elapsedSeconds}
    data-start={clock.sceneStartFrame}/>;
}
"""
    with scene_page(tmp_path, source, frames=4, extra={"timeline": {
            "sceneStartFrame": 100, "sceneEndFrame": 104, "durationInFrames": 4}}) as (page, _):
        for frame in range(4):
            page.evaluate('n => window.__M2V_CODE__.advanceToFrame(n)', frame)
            state = page.locator('#state').evaluate(
                "el => [Number(el.dataset.globalFrame), Number(el.dataset.globalSeconds),"
                " Number(el.dataset.local), Number(el.dataset.start)]")
            assert state == pytest.approx([100 + frame, (100 + frame) / 60, frame / 60, 100])


@pytest.mark.slow
@requires_node
def test_pure_time_supports_absolute_seek_and_subframes(tmp_path, chromium_ready):
    source = """
import {useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
export default function Demo() {
  const clock = useSceneContext();
  useEffect(() => {clock.ready();}, []);
  return <div id="state" data-local={clock.elapsedSeconds} data-global={clock.globalSeconds}/>;
}
"""
    with scene_page(tmp_path, source, frames=12, extra={
            "captureMode": "pure-time", "captureStartFrame": 8,
            "timeline": {"sceneStartFrame": 100, "sceneEndFrame": 112, "durationInFrames": 12}}) as (page, _):
        for frame, subframe, subframes in [(8, 0, 1), (3, 0, 1), (9, 2, 4), (1, 0, 1)]:
            page.evaluate("""([frame, subframe, subframes]) => window.__M2V_CODE__.seekToSubframe(
                frame, subframe, subframes)""", [frame, subframe, subframes])
            state = page.locator('#state').evaluate(
                "el => [Number(el.dataset.local), Number(el.dataset.global)]")
            position = frame + subframe / subframes
            assert state == pytest.approx([position / 60, (100 + position) / 60])


@pytest.mark.slow
@requires_node
def test_echarts_animation_and_controlled_timers(tmp_path, chromium_ready):
    source = """
import {useEffect} from 'react';
import {Chart, useSceneContext} from 'm2v/code-scene';
const option = {animationDuration: 1000, animationEasing: 'linear',
  xAxis:{data:['A']}, yAxis:{max:100}, series:[{type:'bar',data:[100]}]};
export default function Demo() {
  const {ready, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  useEffect(() => {if (running) {
    window.__ticks = 0; const id = setInterval(() => window.__ticks++, 100);
    return () => clearInterval(id);
  }}, [running]);
  return running ? <Chart option={option} width={300} height={200}/> : null;
}
"""
    with scene_page(tmp_path, source) as (page, _):
        pictures = []
        for frame in range(61):
            page.evaluate('n => window.__M2V_CODE__.advanceToFrame(n)', frame)
            if frame in (0, 30, 60):
                pictures.append(page.locator('canvas').screenshot())
        assert len(set(pictures)) == 3, 'ECharts 必须随虚拟时间推进'
        assert page.evaluate('window.__ticks') == 10


@pytest.mark.slow
@requires_node
def test_video_seeks_to_controlled_playback_time(tmp_path, chromium_ready):
    source = """
import {useSceneContext} from 'm2v/code-scene';
export default function Demo() {
  const {ready} = useSceneContext();
  return <video id="video" src="/clip.mp4" muted loop
    onLoadedData={event => {event.currentTarget.currentTime = 0.25; event.currentTarget.play(); ready();}}/>;
}
"""
    # 通过同一个构建入口生成场景，然后在启动本地服务器前放入测试视频。
    from imageio_ffmpeg import get_ffmpeg_exe
    from unittest.mock import patch
    original = prepare_build

    def with_video(*args):
        root, work, result = original(*args)
        import subprocess
        subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=96x64:rate=60:duration=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        str(work / 'clip.mp4')], check=True, capture_output=True)
        return root, work, result

    with patch('helpers.scene_film.prepare_build', with_video), scene_page(tmp_path, source, frames=65) as (page, _):
        for frame in range(61):
            page.evaluate('n => window.__M2V_CODE__.advanceToFrame(n)', frame)
            if frame == 0:
                base = page.locator('video').evaluate('v => v.currentTime')
            assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(base + frame / 60, abs=.001)
            if frame == 30:
                page.wait_for_timeout(120)
                assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(base + .5, abs=.001)
        page.locator('video').evaluate('v => {v.currentTime=1.95; v.playbackRate=2;}')
        page.evaluate('window.__M2V_CODE__.advanceToFrame(61)')
        assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(1.95 + 2/60, abs=.001)
        page.evaluate('window.__M2V_CODE__.advanceToFrame(62)')
        assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(1/60, abs=.001)
        page.locator('video').evaluate('v => v.pause()')
        page.evaluate('window.__M2V_CODE__.advanceToFrame(63)')
        assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(1/60, abs=.001)
        page.locator('video').evaluate('v => v.play()')
        page.evaluate('window.__M2V_CODE__.advanceToFrame(64)')
        assert page.locator('video').evaluate('v => v.currentTime') == pytest.approx(.05, abs=.001)
