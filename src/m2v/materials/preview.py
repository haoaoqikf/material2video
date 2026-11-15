"""候选接触表、短预览与安全静态 HTML；复用现有单视频接触表。

预览不改变源媒体，不把裁剪后的显示偏移写回候选时间；HTML 不执行脚本、
不加载外部资源、不嵌入敏感地址。
"""
from __future__ import annotations

import html
import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw

from .contracts import CandidateData, TimeRange, fingerprint
from .errors import MaterialError
from .media import LOCAL_INPUT_OPTIONS
from .paths import no_links
from .store import MaterialStore

logger = logging.getLogger(__name__)

MAX_PREVIEW_SECONDS = 12.0


@dataclass
class PreviewResult:
    directory: Path
    sheet: Path | None
    html: Path | None
    candidates: list[dict]


def _frame_times(window: TimeRange | None, duration_us: int | None, count: int = 3) -> list[float]:
    if window is None or duration_us is None:
        return []
    start, end = window.startUs / 1_000_000, window.endUs / 1_000_000
    span = max(0.05, end - start)
    inset = min(0.3, span / 4)
    values = [start + inset, start + span / 2, end - inset]
    return [round(min(max(value, 0), max(0, duration_us / 1_000_000 - 0.05)), 3) for value in values[:count]]


def _preview_clip(source: Path, window: TimeRange | None, target: Path, *,
                  seconds: float, width: int, has_audio: bool) -> dict:
    duration = window.endUs - window.startUs if window else None
    limit_us = int(min(seconds, MAX_PREVIEW_SECONDS) * 1_000_000)
    start_us = window.startUs if window else 0
    take_us = min(duration or limit_us, limit_us)
    command = [get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(source), *LOCAL_INPUT_OPTIONS,
               '-ss', f'{start_us / 1_000_000:.6f}', '-t', f'{take_us / 1_000_000:.6f}',
               '-map', '0:v:0', '-vf', f'scale={width}:-2', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '23', '-pix_fmt', 'yuv420p']
    command += (['-map', '0:a:0', '-c:a', 'aac', '-b:a', '128k'] if has_audio else ['-an'])
    command += ['-y', str(target)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '短预览生成超时', stage='preview') from exc
    if result.returncode or not target.is_file() or not target.stat().st_size:
        raise MaterialError('decode-failed', '短预览生成失败', stage='preview')
    return {'path': target.name, 'startUs': start_us, 'durationUs': take_us,
            'truncated': bool(duration and take_us < duration)}


def _composite(sheets: list[Path], labels: list[str], target: Path, *, width: int = 480) -> None:
    images = []
    for path in sheets:
        with Image.open(path) as opened:
            images.append(opened.convert('RGB').copy())
    if not images:
        raise MaterialError('invalid-request', '没有可拼接的候选接触表', stage='preview')
    cell_width = width
    cell_height = max(image.height * width // max(1, image.width) for image in images)
    gap, header = 10, 26
    canvas = Image.new('RGB', (cell_width + gap * 2, (cell_height + header + gap) * len(images) + gap),
                       (17, 17, 17))
    draw = ImageDraw.Draw(canvas)
    for index, (image, label) in enumerate(zip(images, labels)):
        y = gap + index * (cell_height + header + gap)
        draw.text((gap, y + 4), label, fill=(241, 236, 221))
        image.thumbnail((cell_width, cell_height), Image.LANCZOS)
        canvas.paste(image, (gap + (cell_width - image.width) // 2, y + header))
    canvas.save(target, format='PNG')


def _source_url(store: MaterialStore, candidate: CandidateData) -> str | None:
    try:
        return store.get(candidate.sourceId, kind='material.source').data.sourceUrl
    except MaterialError:
        return None


def _selection_export(candidates: list[CandidateData], entries: list[dict]) -> list[dict]:
    result = []
    for candidate, entry in zip(candidates, entries):
        result.append({'candidateId': entry['candidateId'], 'candidateDigest': entry['candidateDigest'],
                       'mediaId': candidate.mediaId, 'mediaSha256': candidate.mediaSha256,
                       'localRange': candidate.localRange.model_dump(mode='json') if candidate.localRange else None,
                       'sourceRange': candidate.sourceRange.model_dump(mode='json') if candidate.sourceRange else None,
                       'decision': 'chosen', 'rationale': '', 'purpose': '', 'operator': '',
                       'audio': 'preserve', 'fps': 30})
    return result


def _write_html(path: Path, entries: list[dict], selections: list[dict]) -> None:
    cards = []
    for entry in entries:
        reasons = '；'.join(f"{reason['channel']}#{reason['rank']} {reason['excerpt']}" for reason in entry['reasons'])
        link = (f'<a href="{html.escape(entry["sourceUrl"])}" rel="noreferrer noopener" target="_blank">原始来源页</a>'
                if entry.get('sourceUrl') else '来源页未知')
        preview = (f'<video controls preload="none" src="{html.escape(entry["preview"])}"></video>'
                   if entry.get('preview') else '')
        limitations = ''.join(f'<li>{html.escape(note)}</li>' for note in entry['limitations'])
        cards.append(f'''<section class="card">
<h2>{html.escape(entry["label"])}</h2>
<img src="{html.escape(entry["sheet"])}" alt="{html.escape(entry["label"])} 接触表">
{preview}
<p class="meta">本地窗口 {entry["localRange"] or "整图"}；源区间 {entry["sourceRange"] or "未知"}；融合分 {entry["fusionScore"]}</p>
<p class="reasons">{html.escape(reasons)}</p>
{link}
<ul class="notes">{limitations}</ul>
</section>''')
    data = html.escape(json.dumps(selections, ensure_ascii=False, indent=2))
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file: data:; media-src 'self' file:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>素材候选比较</title>
<style>
body{{background:#111;color:#e8e4da;font:15px/1.6 system-ui,"Noto Sans CJK SC",sans-serif;margin:0;padding:24px}}
h1{{font-size:22px;font-weight:600}} h2{{font-size:17px;margin:0 0 8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:18px}}
.card{{border:1px solid #333;padding:14px;background:#171717}}
img,video{{max-width:100%;height:auto;display:block;margin:8px 0}}
.meta{{color:#9a958a;font-size:13px}} .reasons{{color:#c9c4b8}}
.notes{{color:#9a958a;font-size:12px;padding-left:18px}}
pre{{white-space:pre-wrap;background:#0b0b0b;border:1px solid #333;padding:12px;font-size:12px}}
a{{color:#8fb8ff}}
</style></head><body>
<h1>素材候选比较</h1>
<p class="meta">静态页面，不执行脚本、不联网加载资源。观察状态默认未知，融合分仅用于排序。</p>
<div class="grid">{''.join(cards)}</div>
<h2>选择清单（复制到选择 JSON 后由 select 处理）</h2>
<pre>{data}</pre>
</body></html>'''
    path.write_text(document, encoding='utf-8')


def preview_candidates(store: MaterialStore, candidates: list[CandidateData], *,
                       out: Path, columns: int = 3, tile_width: int = 480,
                       preview_seconds: float = 6.0, html_output: bool = True) -> PreviewResult:
    if not candidates:
        raise MaterialError('invalid-request', '没有候选可预览', stage='preview')
    if len(candidates) > 12:
        raise MaterialError('resource-limit', '单次预览最多 12 个候选', stage='preview')
    if type(columns) is not int or not 1 <= columns <= 8:
        raise MaterialError('invalid-request', '接触表列数必须为 1..8', stage='preview')
    if type(tile_width) is not int or not 160 <= tile_width <= 1920:
        raise MaterialError('invalid-request', '接触表单格宽度必须为 160..1920', stage='preview')
    if not 0 < preview_seconds <= MAX_PREVIEW_SECONDS:
        raise MaterialError('invalid-request', f'短预览时长必须在 (0, {MAX_PREVIEW_SECONDS}] 秒', stage='preview')
    from m2v.engine.assets_tools import contact_sheet
    root = no_links(out)
    root.mkdir(parents=True, exist_ok=True)
    entries, sheets, labels = [], [], []
    with tempfile.TemporaryDirectory(prefix='contact-', dir=root) as temporary:
        for index, candidate in enumerate(candidates, start=1):
            media = store.get(candidate.mediaId, kind='material.media')
            if media.data.artifact.sha256 != candidate.mediaSha256:
                raise MaterialError('hash-mismatch', '候选媒体摘要已变化，请重新查找', stage='preview')
            source_path = store.verify_artifact(media.data.artifact)
            image = media.data.probe.kind == 'image'
            # 内容对象按摘要命名、没有扩展名；接触表按后缀判断类型，复制到暂存再调用。
            suffix = ('.png' if image else '.mp4')
            display_path = Path(temporary) / f'candidate-{index:02d}{suffix}'
            shutil.copyfile(source_path, display_path)
            times = _frame_times(candidate.localRange, media.data.probe.durationUs)
            sheet_path = root / f'candidate-{index:02d}.png'
            contact_sheet([display_path], times=None if image else times or None,
                          samples=max(1, min(6, len(times) or 1)), columns=min(columns, max(1, len(times) or 1)),
                          tile_width=tile_width, out=sheet_path)
            preview = None
            if not image:
                preview_path = root / f'candidate-{index:02d}-preview.mp4'
                preview = _preview_clip(source_path, candidate.localRange, preview_path,
                                        seconds=preview_seconds, width=min(960, tile_width * 2),
                                        has_audio=media.data.probe.hasAudio)
            label = f'候选 {index} · {media.id}'
            entries.append({'label': label, 'candidateId': f'candidate-{index:02d}',
                            'candidateDigest': fingerprint(candidate.model_dump(mode='json')),
                            'mediaId': media.id, 'mediaSha256': candidate.mediaSha256,
                            'localRange': _window_text(candidate.localRange),
                            'sourceRange': _window_text(candidate.sourceRange),
                            'fusionScore': candidate.fusionScore,
                            'sheet': sheet_path.name, 'preview': preview['path'] if preview else None,
                            'previewRange': preview, 'sourceUrl': _source_url(store, candidate),
                            'reasons': [reason.model_dump(mode='json') for reason in candidate.retrievalReasons],
                            'limitations': list(candidate.limitations)})
            sheets.append(sheet_path)
            labels.append(label)
        composite = root / 'candidates.png'
        _composite(sheets, labels, composite, width=tile_width)
        html_path = root / 'candidates.html' if html_output else None
        selections = _selection_export(candidates, entries)
        if html_path is not None:
            _write_html(html_path, entries, selections)
    index = {'schemaVersion': 1, 'directory': str(root), 'sheet': composite.name,
             'html': html_path.name if html_path else None, 'candidates': entries,
             'selectionTemplate': selections}
    (root / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return PreviewResult(directory=root, sheet=composite, html=html_path, candidates=entries)


def _window_text(window: TimeRange | None) -> str | None:
    if window is None:
        return None
    return f'{window.startUs}-{window.endUs} us'
