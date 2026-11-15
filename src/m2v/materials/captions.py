"""SRT/VTT/ASS 字幕与章节的本地解析和严格时间校验。

字幕文字与时间只是来源声明，不代表与当前画面版本对齐，也不等于画面命中。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .contracts import TimeRange, fingerprint
from .errors import MaterialError

MAX_CUES = 100_000
MAX_TEXT = 8_000
_TAG = re.compile(r'<[^>]{0,200}>')
_CJK = re.compile(r'[㐀-䶿一-鿿]')


@dataclass(frozen=True)
class Cue:
    range: TimeRange
    text: str


@dataclass
class CaptionParse:
    cues: list[Cue]
    language: str | None
    limitations: list[str] = field(default_factory=list)
    format: str = 'srt'

    @property
    def overlapping(self) -> int:
        ordered = sorted(self.cues, key=lambda cue: (cue.range.startUs, cue.range.endUs))
        return sum(1 for left, right in zip(ordered, ordered[1:]) if right.range.startUs < left.range.endUs)


def _decode(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > 32 * 1024 * 1024:
        raise MaterialError('resource-limit', '字幕文件超过 32 MiB 预算', stage='captions')
    for encoding in ('utf-8-sig', 'utf-16', 'gb18030', 'big5'):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode('utf-8', errors='replace')


def _clock(value: str, *, separator: str) -> int | None:
    pattern = rf'^\s*(\d{{1,2}}):(\d{{2}}):(\d{{2}})[{separator}](\d{{1,3}})\s*$'
    match = re.fullmatch(pattern, value)
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    if int(minutes) > 59 or int(seconds) > 59:
        return None
    scale = {'1': 100_000, '2': 10_000, '3': 1_000}[str(len(fraction))]
    return ((int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1_000_000
            + int(fraction) * scale)


def _clean(value: str) -> str:
    value = _TAG.sub(' ', value)
    value = value.replace('\\N', ' ').replace('\\n', ' ')
    value = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()[:MAX_TEXT]


def _srt(text: str) -> list[tuple[int, int, str]]:
    cues = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n')):
        lines = [line for line in block.split('\n')]
        index = next((position for position, line in enumerate(lines) if '-->' in line), None)
        if index is None:
            continue
        left, _, right = lines[index].partition('-->')
        start, end = _clock(left, separator=','), _clock(right.split()[0] if right.split() else '', separator=',')
        if start is None or end is None:
            continue
        body = _clean(' '.join(lines[index + 1:]))
        if body:
            cues.append((start, end, body))
    return cues


def _vtt(text: str) -> list[tuple[int, int, str]]:
    cues = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n')):
        if block.lstrip().startswith(('WEBVTT', 'NOTE', 'STYLE', 'REGION')):
            continue
        lines = block.split('\n')
        index = next((position for position, line in enumerate(lines) if '-->' in line), None)
        if index is None:
            continue
        left, _, right = lines[index].partition('-->')
        start, end = _clock(left, separator='.'), _clock(right.strip().split()[0] if right.strip() else '', separator='.')
        if start is None or end is None:
            continue
        body = _clean(' '.join(lines[index + 1:]))
        if body:
            cues.append((start, end, body))
    return cues


def _ass(text: str) -> list[tuple[int, int, str]]:
    cues, fields = [], None
    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        stripped = line.strip()
        if stripped.lower().startswith('format:') and fields is None:
            fields = [item.strip().lower() for item in stripped.split(':', 1)[1].split(',')]
            continue
        if stripped.lower().startswith('[events]'):
            fields = fields or ['layer', 'start', 'end', 'style', 'name', 'marginl', 'marginr', 'marginv',
                                'effect', 'text']
            continue
        if not stripped.lower().startswith('dialogue:') or fields is None:
            continue
        values = stripped.split(':', 1)[1].split(',', len(fields) - 1)
        record = dict(zip(fields, values))
        start = _clock(record.get('start', '').strip(), separator=r'\.')
        end = _clock(record.get('end', '').strip(), separator=r'\.')
        body = _clean(record.get('text', ''))
        if start is not None and end is not None and body:
            cues.append((start, end, body))
    return cues


def detect_format(path: Path, text: str) -> str:
    suffix = path.suffix.lower()
    if suffix == '.ass':
        return 'ass'
    if suffix == '.vtt' or text.lstrip().startswith('WEBVTT'):
        return 'vtt'
    return 'srt'


def language_of(values: list[str]) -> str | None:
    cjk = sum(len(_CJK.findall(value)) for value in values)
    latin = sum(1 for value in values for char in value if char.isascii() and char.isalpha())
    if not cjk and not latin:
        return None
    if cjk and latin and min(cjk, latin) / max(cjk, latin) > 0.15:
        return 'mixed'
    return 'zh' if cjk else 'en'


def parse_captions(path: Path, *, duration_us: int | None) -> CaptionParse:
    text = _decode(path)
    format = detect_format(path, text)
    raw = {'srt': _srt, 'vtt': _vtt, 'ass': _ass}[format](text)
    limitations: list[str] = []
    if len(raw) > MAX_CUES:
        limitations.append(f'字幕条目超过 {MAX_CUES} 条，只保留前 {MAX_CUES} 条')
        raw = raw[:MAX_CUES]
    cues, clamped, invalid = [], 0, 0
    for start, end, body in raw:
        if end <= start:
            invalid += 1
            continue
        if duration_us is not None:
            if start >= duration_us:
                invalid += 1
                continue
            if end > duration_us:
                end = duration_us
                clamped += 1
                if end <= start:
                    invalid += 1
                    continue
        cues.append(Cue(TimeRange(startUs=start, endUs=end), body))
    if not cues:
        limitations.append('未解析到有效字幕条目；空语音或格式不受支持时不冒充已对齐字幕')
    if clamped:
        limitations.append(f'{clamped} 条字幕越过实测媒体末尾，已按媒体时长截断')
    if invalid:
        limitations.append(f'{invalid} 条字幕时间为零长度、倒序或完全越界，已丢弃')
    overlapping = 0
    ordered = sorted(cues, key=lambda cue: (cue.range.startUs, cue.range.endUs))
    overlapping = sum(1 for left, right in zip(ordered, ordered[1:]) if right.range.startUs < left.range.endUs)
    if overlapping:
        limitations.append(f'{overlapping} 处字幕时间重叠；保留原文但时间关系不保证唯一')
    language = language_of([cue.text for cue in cues])
    if language == 'mixed':
        limitations.append('字幕含中文与其它语言混排；语言按条目来源记录，不保证逐句准确')
    return CaptionParse(cues=cues, language=language, limitations=limitations, format=format)


def cue_records(cues: list[Cue], *, channel: str = 'captions', language: str | None,
                origin: str, alignment: str = 'unverified', source_key: str = '') -> list[dict]:
    """生成稳定 ID；同一媒体多条字幕轨不会因文字相同而互相覆盖。"""
    records = []
    for index, cue in enumerate(cues):
        identifier = fingerprint({'channel': channel, 'source': source_key, 'index': index,
                                  'text': cue.text, 'start': cue.range.startUs,
                                  'end': cue.range.endUs})[:24]
        records.append({'id': f'{channel}-{identifier}', 'channel': channel, 'text': cue.text,
                        'localRange': cue.range.model_dump(mode='json'), 'language': language,
                        'alignment': alignment, 'origin': origin})
    return records


def chapters_to_records(chapters, *, alignment: str = 'unverified') -> list[dict]:
    records = []
    for index, chapter in enumerate(chapters):
        identifier = fingerprint({'channel': 'chapters', 'index': index, 'title': chapter.title,
                                  'start': chapter.localRange.startUs,
                                  'end': chapter.localRange.endUs})[:24]
        records.append({'id': f'chapters-{identifier}', 'channel': 'chapters', 'text': chapter.title,
                        'localRange': chapter.localRange.model_dump(mode='json'),
                        'alignment': alignment, 'origin': 'source-chapters'})
    return records
