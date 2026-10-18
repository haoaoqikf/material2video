"""交付文件的帧序列与音频信号检查；候选不是审美通过结论。"""
from __future__ import annotations

from array import array
import hashlib
import logging
import math
from pathlib import Path
import re
import subprocess
import tempfile
import time

from imageio_ffmpeg import get_ffmpeg_exe
from m2v.core.errors import M2VError

logger = logging.getLogger(__name__)


def command(args: list[str], *, info: bool = False) -> str:
    result = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostats',
                             '-v', 'info' if info else 'error', *args],
                            capture_output=True, timeout=900)
    if result.returncode:
        raise M2VError('替代验收检测失败：' + result.stderr.decode('utf-8', 'replace')[-1600:])
    return result.stderr.decode('utf-8', 'replace')


def shots(prepared: dict) -> list[dict]:
    result = []
    for scene in prepared['props'].get('compiledScenes', []):
        start = scene.get('startFrame', 0)
        declared = (scene.get('content', {}).get('props') or {}).get('shots') or []
        if not declared:
            declared = [{'id': scene['id'], 'startFrame': 0,
                         'endFrame': scene.get('durationInFrames', prepared['durationInFrames'] - start)}]
        for shot in declared:
            result.append({**shot, 'startFrame': start + shot['startFrame'],
                           'endFrame': start + shot['endFrame']})
    return result


def sample_indices(prepared: dict, intervals: list[dict] = ()) -> list[int]:
    """完整逐秒覆盖，并在镜头交界、hero/风险和异常时间窗按0.1秒加密。"""
    count, fps = prepared['durationInFrames'], prepared['fps']
    if count < 1 or fps < 1:
        raise M2VError('替代验收需要有效帧数和帧率')
    picks = {0, count - 1, *range(0, count, fps)}
    dense = max(1, round(fps / 10))
    spans = []
    for shot in shots(prepared):
        a, b = shot['startFrame'], shot['endFrame'] - 1
        picks.update((a, b, (a + b) // 2))
        spans.extend(((a - fps // 2, a + fps // 2), (b - fps // 2, b + fps // 2)))
        if shot.get('tier') == 'hero':
            spans.append((a, b))
    for item in intervals:
        spans.append((math.floor((item['startSeconds'] - .5) * fps),
                      math.ceil((item['endSeconds'] + .5) * fps)))
    for a, b in spans:
        picks.update(range(max(0, a), min(count - 1, b) + 1, dense))
    return sorted(n for n in picks if 0 <= n < count)


def video_candidates(video: Path, seconds: float) -> dict:
    """一次解码定位黑场和突变；只输出候选，正常黑底和硬切需要上下文复查。"""
    log = command(['-i', str(video), '-an', '-vf',
                   r'blackdetect=d=0.1:pix_th=0.10:pic_th=0.98,select=gt(scene\,0.3),showinfo',
                   '-f', 'null', '-'], info=True)
    black = [{'startSeconds': float(a), 'endSeconds': float(b), 'reason': 'black-frame'}
             for a, b in re.findall(r'black_start:([\d.]+)\s+black_end:([\d.]+)', log)]
    changes = [{'startSeconds': max(0, float(t) - .1),
                'endSeconds': min(seconds, float(t) + .1), 'reason': 'frame-change'}
               for t in re.findall(r'\[Parsed_showinfo[^\]]*\].*?pts_time:([\d.]+)', log)]
    return {'kind': 'measurement', 'status': 'measured', 'candidates': black + changes,
            'detail': '黑场或突变仅供定位，需查看加密帧并对照镜头设计。'}


def _audio_format(video: Path) -> tuple[int, int] | None:
    if not video.is_file() or not video.stat().st_size:
        raise M2VError('缺少有效的交付文件：' + str(video))
    result = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-i', str(video)],
                            capture_output=True, timeout=120)
    info = result.stderr.decode('utf-8', 'replace')
    line = next((line for line in info.splitlines() if 'Stream #' in line and 'Audio:' in line), None)
    if line is None:
        return None
    match = re.search(r'(\d+) Hz, ([^,]+),', line)
    if not match:
        raise M2VError('无法识别交付音轨采样率和声道')
    layout = match[2].strip()
    channels = {'mono': 1, 'stereo': 2, '2.1': 3, 'quad': 4, '5.1': 6, '5.1(side)': 6, '7.1': 8}.get(layout)
    if channels is None:
        explicit = re.match(r'(\d+) channels', layout)
        channels = int(explicit[1]) if explicit else None
    if channels is None:
        raise M2VError('不支持的音轨声道布局：' + layout)
    return int(match[1]), channels


def narration_windows(prepared: dict) -> list[dict]:
    result = []
    fps = prepared['fps']
    # prepared 的 segmentWindows 已经是全片绝对帧号（准备阶段把 scene.startFrame 与
    # 本幕旁白起点一起写进去了）；再叠加一次幕起点会让第二幕以后的窗口整体后移。
    for scene in prepared['props'].get('compiledScenes', []):
        for segment in scene.get('narrationSegments', []):
            if not segment.get('text', '').strip():
                continue
            window = scene.get('segmentWindows', {}).get(segment['id'])
            if window:
                result.append({'id': segment['id'], 'startSeconds': window['startFrame'] / fps,
                               'endSeconds': window['endFrame'] / fps})
    return result


def audio_signals(video: Path, prepared: dict, *, required: bool) -> dict:
    """流式扫描原采样率、原声道的PCM，内存只保留半秒；stderr落临时文件避免死锁。"""
    fmt = _audio_format(video)
    if fmt is None:
        if required:
            raise M2VError('有声作品的交付文件缺少音轨')
        return {'kind': 'measurement', 'status': 'not-applicable', 'candidates': [], 'detail': '契约允许无音轨'}
    rate, channels = fmt
    chunk_samples = max(channels, rate // 2 * channels)
    clips, total = [], 0
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen([get_ffmpeg_exe(), '-hide_banner', '-nostats', '-i', str(video),
                                 '-vn', '-map', '0:a:0', '-af', 'silencedetect=n=-45dB:d=0.5',
                                 '-c:a', 'pcm_f32le', '-f', 'f32le', '-'],
                                stdout=subprocess.PIPE, stderr=errors)
        try:
            while raw := proc.stdout.read(chunk_samples * 4):
                samples = array('f')
                samples.frombytes(raw)
                peak_count = sum(abs(value) >= .9999 for value in samples)
                end = total + len(samples)
                if peak_count:
                    clips.append({'startSeconds': total / (rate * channels),
                                  'endSeconds': end / (rate * channels), 'samples': peak_count,
                                  'reason': 'clipping-candidate'})
                total = end
            code = proc.wait(timeout=900)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()
        errors.seek(0)
        log = errors.read().decode('utf-8', 'replace')
    if code or not total:
        raise M2VError('交付音轨信号检查失败：' + log[-1200:])
    duration = total / (rate * channels)
    silences = []
    start = None
    for kind, value in re.findall(r'silence_(start|end):\s*([\d.]+)', log):
        if kind == 'start':
            start = float(value)
        elif start is not None:
            silences.append({'startSeconds': start, 'endSeconds': float(value), 'reason': 'silence'})
            start = None
    if start is not None:
        silences.append({'startSeconds': start, 'endSeconds': duration, 'reason': 'silence'})
    windows = narration_windows(prepared)
    for item in silences:
        item['narrationOverlap'] = [w['id'] for w in windows if max(w['startSeconds'], item['startSeconds'])
                                    < min(w['endSeconds'], item['endSeconds'])]
    expected = prepared['durationInFrames'] / prepared['fps']
    timing = [dict(w, reason='narration-out-of-track') for w in windows
              if w['startSeconds'] < 0 or w['endSeconds'] > duration + .1 or w['endSeconds'] <= w['startSeconds']]
    if abs(duration - expected) > .1:
        timing.append({'startSeconds': min(duration, expected), 'endSeconds': max(duration, expected),
                       'reason': 'audio-duration-mismatch'})
    return {'kind': 'measurement', 'status': 'measured', 'durationSeconds': round(duration, 5),
            'sampleRate': rate, 'channels': channels, 'durationDifference': round(abs(duration - expected), 5),
            'narrationWindows': windows, 'timingGranularity': 'segment',
            'candidates': silences + clips + timing,
            'detail': '静音/削波是候选；结合旁白边界和设计停顿复核，不证明口播内容或听感。'}


def extract_sequence(video: Path, prepared: dict, outputs: Path, intervals: list[dict] = ()) -> dict:
    indices = sample_indices(prepared, intervals)
    outputs = outputs.resolve()
    outputs.mkdir(parents=True, exist_ok=True)
    # 每次写入独立子目录，失败不让旧图像冒充新检查；只保存选中帧，不落全片PNG。
    work = Path(tempfile.mkdtemp(prefix='sequence-', dir=outputs))
    expression = '+'.join(f'eq(n\\,{i})' for i in indices)
    # filter脚本避免长片的数千个采样点超过Windows命令行长度上限。
    filters = work / 'sequence.ffscript'
    filters.write_text(f"select={expression},scale=960:-2,drawtext=text='%{{pts\\:hms}}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.8:x=8:y=h-th-8", encoding='utf-8')
    command(['-i', str(video), '-an', '-filter_script:v', str(filters),
             '-fps_mode', 'vfr', '-q:v', '3', str(work / 'frame-%06d.jpg')])
    images = sorted(work.glob('frame-*.jpg'))
    if len(images) != len(indices):
        raise M2VError(f'帧序列采样数量不匹配：期望{len(indices)}，实际{len(images)}')
    pages = []
    for page, first in enumerate(range(0, len(images), 16), 1):
        sheet = work / f'contact-{page:03d}.jpg'
        command(['-start_number', str(first + 1), '-i', str(work / 'frame-%06d.jpg'),
                 '-vf', 'scale=480:-2,tile=4x4', '-frames:v', '1', '-q:v', '3', str(sheet)])
        pages.append(sheet.relative_to(outputs.parent).as_posix())
    samples = [{'frame': frame, 'seconds': round(frame / prepared['fps'], 5),
                'path': image.relative_to(outputs.parent).as_posix()} for frame, image in zip(indices, images)]
    return {'method': 'frame-sequence', 'coverage': 'full-timeline-sampled',
            'samples': samples, 'pages': pages, 'firstFrame': indices[0], 'lastFrame': indices[-1],
            'detail': '逐秒、逐镜头与交界/风险/异常加密采样，不等于逐帧完整观看。'}


def inspect(video: Path, prepared: dict, outputs: Path, *, audio_required: bool) -> dict:
    started = time.monotonic()
    logger.info('替代验收开始：%s，%d帧', video, prepared['durationInFrames'])
    seconds = prepared['durationInFrames'] / prepared['fps']
    visual = video_candidates(video, seconds)
    audio = audio_signals(video, prepared, required=audio_required)
    intervals = visual['candidates'] + audio['candidates']
    sequence = extract_sequence(video, prepared, outputs, intervals)
    # 流式摘要，不把数百MB交付文件读进内存。
    with video.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    elapsed = round(time.monotonic() - started, 3)
    logger.info('替代验收检测完成：%d采样，%d页，%.3f秒；候选需实际复查',
                len(sequence['samples']), len(sequence['pages']), elapsed)
    return {'videoSha256': digest, 'preparedFingerprint': prepared['preparedFingerprint'],
            'elapsedSeconds': elapsed,
            'sequence': sequence, 'videoSignals': visual, 'audioSignals': audio,
            'observation': 'not-evaluated', 'reviewRequired': True,
            'limitations': ['未连续播放或实际试听', '配音自然度、口播误读、音乐感染力未验证', '采样间瞬时缺陷可能遗漏']}
