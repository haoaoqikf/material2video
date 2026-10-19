"""先以15fps简化场景检查完整旅程；保留真实秒时钟，不授权正式导出。"""
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from m2v.types.general import code_scenes
from m2v.engine import audio, frames

ROOT = Path(__file__).resolve().parents[1]


def main():
    board = json.loads((ROOT / 'storyboard.json').read_text(encoding='utf-8'))
    scene = board['scenes'][0]
    proposal = json.loads((ROOT / 'outputs/path-proposal.json').read_text(encoding='utf-8'))
    work = ROOT / 'outputs/rough-motion-v2'
    work.mkdir(parents=True, exist_ok=True)
    compiled = {**scene, 'content': {**scene['content'], 'entry': 'scenes/rough.tsx'},
                'startFrame': 0, 'durationInFrames': scene['durationFrames'],
                'segmentWindows': proposal['report']['windows']}
    config = code_scenes.scene_config(compiled, frames.spec(1920, 1080), {}, profile='standard')
    config.update(fps=15, width=960, height=540, durationInFrames=(scene['durationFrames']+3)//4)
    code_scenes.build_scene(ROOT, compiled, work)
    import sys
    if '--reuse-frames' not in sys.argv:
        with sync_playwright() as pw:
            code_scenes._capture(pw, ROOT, work, config)
    output = work / 'rough.mp4'
    # 临时声音：当前准备母版已按同一时间窗包含旁白与音乐，直接复用；尚无准备产物时
    # 退回原创循环底，只用于判断节奏，不冒充有声预演。
    prepared_path = ROOT / 'outputs/prepared.json'
    prepared = None
    if prepared_path.exists():
        candidate = json.loads(prepared_path.read_text(encoding='utf-8'))
        if (candidate.get('durationInFrames') != scene['durationFrames']
                or candidate.get('fps') != board['fps']):
            print('准备产物与当前分镜时长/帧率不一致，粗预演退回临时音乐床')
        else:
            prepared = candidate
    if prepared:
        source = ROOT / prepared['audio']['segments'][0]['path']
        audio_args = ['-i', str(source)]
        audio_filter = []
    else:
        source = ROOT / 'assets/sound/bed.wav'
        audio_args = ['-stream_loop', '-1', '-i', str(source)]
        audio_filter = ['-filter_complex', '[1:a]volume=0.2[a]']
    audio.ffmpeg(['-framerate','15','-i',str(work/'frame-%06d.png'),*audio_args,*audio_filter,
                  '-map','0:v','-map','1:a' if not audio_filter else '[a]',
                  '-t',str(scene['durationFrames']/60),
                  '-c:v','libx264','-crf','23','-pix_fmt','yuv420p','-c:a','aac',str(output)])
    (work/'record.json').write_text(json.dumps({'temporary':True,'seconds':scene['durationFrames']/60,
        'fps':15,'audio':'prepared-master' if prepared else 'bed-only',
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'storyboardSha256':hashlib.sha256((ROOT/'storyboard.json').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
