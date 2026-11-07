"""只针对异步绘制完成边界的真实浏览器和原生采集验证。"""
from pathlib import Path

import pytest
from PIL import Image

from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project
from m2v.production import ledger, samples
from m2v.production.storage import read, write
from helpers.scene_film import requires_node, scene_page

EXAMPLE = Path(__file__).parents[1] / 'fixtures/code-scenes/async-bitmap.tsx'


@pytest.mark.slow
@requires_node
def test_async_bitmap_waits_at_initial_start_and_absolute_subframes(tmp_path, chromium_ready):
    with scene_page(tmp_path, EXAMPLE.read_text(encoding='utf-8'), frames=12,
                    extra={'captureMode': 'pure-time', 'captureStartFrame': 8}) as (page, _):
        def pixel():
            return page.locator('canvas').evaluate('c => [...c.getContext("2d").getImageData(10,10,1,1).data]')
        assert pixel() == [127, 81, 119, 255]
        images = {}
        for frame, part, total in [(8, 0, 1), (1, 0, 1), (9, 1, 2), (8, 0, 1)]:
            page.evaluate('p => window.__M2V_CODE__.seekToSubframe(...p)', [frame, part, total])
            position = frame + part / total
            assert pixel() == [round(31 + position * 12), 81, 119, 255]
            shot = page.locator('canvas').screenshot()
            if position in images:
                assert shot == images[position]
            images[position] = shot


@pytest.mark.slow
@requires_node
def test_first_seek_finishes_start_work_before_changing_time(tmp_path, chromium_ready):
    source = EXAMPLE.read_text(encoding='utf-8').replace('waitForFrame(draw());', '''
    if (running && !window.__startupHeld) {
      window.__startupHeld = true;
      waitForFrame(new Promise<void>(resolve => {
        window.__releaseStartup = () => {void draw().then(resolve);};
      }));
    } else waitForFrame(draw());''').replace(
        'return <canvas', 'return <canvas data-requested={elapsedSeconds * config.fps}')
    with scene_page(tmp_path, source, frames=12,
                    extra={'captureMode': 'pure-time', 'captureStartFrame': 8}) as (page, _):
        origin = page.evaluate('performance.now()')
        page.evaluate('''() => {
          window.__pendingSeek = window.__M2V_CODE__.seekToSubframe(3,0,1);
        }''')
        assert page.locator('canvas').get_attribute('data-requested') == '8'
        assert page.evaluate('performance.now()') == origin
        with pytest.raises(Exception, match='不能重叠'):
            page.evaluate('window.__M2V_CODE__.seekToSubframe(4,0,1)')
        page.evaluate('window.__releaseStartup()')
        page.evaluate('window.__pendingSeek')
        assert page.locator('canvas').get_attribute('data-requested') == '3'
        assert page.locator('canvas').evaluate(
            'c => [...c.getContext("2d").getImageData(10,10,1,1).data]') == [67, 81, 119, 255]


@pytest.mark.media
@requires_node
def test_async_capture_encodes_current_pixels_and_failure_publishes_nothing(tmp_path, chromium_ready):
    root = tmp_path / 'work'
    create_project(root, 'text-motion', {'storyboard': 'storyboard.json'})
    config = read(root / 'project.json')
    config['output'].update(width=1920, height=1080, fps=30)
    write(root / 'project.json', config)
    root, project = load_project(root)
    (root / 'scenes').mkdir()
    (root / 'scenes/main.tsx').write_text(EXAMPLE.read_text(encoding='utf-8'), encoding='utf-8')
    options = dict(entry='scenes/main.tsx', props={'capture': {'mode': 'pure-time', 'verifyFrames': 3}},
                   duration_seconds=4/30, still_frames=[0, 1, 3])
    result = samples.capture(root, project, **options)
    for frame in [0, 1, 3]:
        with Image.open(root / f'outputs/samples/{result["id"]}/still-{frame:06d}.png') as image:
            assert image.convert('RGB').getpixel((10, 10)) == (31 + frame * 12, 81, 119)
    before = ledger.history(root)[0]
    options['props'] = {**options['props'], 'rejectFrame': 2}
    with pytest.raises(M2VError, match='async-bitmap-failure'):
        samples.capture(root, project, **options)
    assert ledger.history(root)[0] == before
    assert not list((root / 'outputs/samples').glob('.sample-*'))
