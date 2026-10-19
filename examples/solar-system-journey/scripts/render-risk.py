"""正式画幅的运动风险帧：覆盖所有换站、进出站与hero；最终字幕由完整预演再复核。"""
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from m2v.engine import frames
from m2v.types.general import code_scenes, media_assets

ROOT = Path(__file__).resolve().parents[1]


def main():
    board = json.loads((ROOT / 'storyboard.json').read_text(encoding='utf-8'))
    scene = board['scenes'][0]
    report = json.loads((ROOT / 'outputs/path-proposal.json').read_text(encoding='utf-8'))['report']
    windows = report['windows']
    compiled = {**scene, 'startFrame': 0, 'durationInFrames': scene['durationFrames'], 'segmentWindows': windows}
    config = code_scenes.scene_config(compiled, frames.spec(1920, 1080), media_assets.resolve(ROOT)['media'], profile='cinematic')
    work = ROOT / 'outputs/motion-risk-v2'
    work.mkdir(parents=True, exist_ok=True)
    selected = {0, scene['durationFrames']-1}
    for shot in scene['content']['props']['shots']:
        start, end = shot['startFrame'], shot['endFrame']
        selected.update(range(start, end, 30))
        selected.add(end-1)
        if shot.get('segment'):
            window = windows[shot['segment']]
            selected.update(range(start, window['startFrame'], 12))
            selected.update(range(max(start, end-120), end, 12))
    # 本片的相机、自转、粒子、后期均按绝对帧求值。只用于诊断取样，正式prepare仍从零逐帧录制。
    indices = sorted(selected)
    compiled['content'] = {**compiled['content'], 'entry': 'scenes/inspection.tsx',
        'props': {**compiled['content']['props'], 'inspectionFrames':indices,
                  'timelineFrames':scene['durationFrames']}}
    config = code_scenes.scene_config(compiled, frames.spec(1920, 1080), media_assets.resolve(ROOT)['media'], profile='cinematic')
    config['durationInFrames'] = len(indices)
    code_scenes.build_scene(ROOT, compiled, work)
    sampled = work / 'sampled'
    if sampled.exists():
        shutil.rmtree(sampled)
    sampled.mkdir()
    with sync_playwright() as pw:
        code_scenes._capture(pw, ROOT, work, config)
    for index, frame in enumerate(indices):
        (work / f'frame-{index:06d}.png').replace(sampled / f'frame-{frame:06d}.png')
    (work / 'record.json').write_text(json.dumps({'frames':indices, 'fps':60,
        'scope':'motion-and-composition; shared subtitles reviewed after full preview'},indent=2),encoding='utf-8')
    print(f'{len(selected)} risk frames: {work}')


if __name__ == '__main__':
    main()
