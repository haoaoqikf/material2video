"""字幕/章节解析：重叠、越界、混语与空语音边界。"""
from __future__ import annotations

from pathlib import Path

from m2v.materials.captions import chapters_to_records, cue_records, language_of, parse_captions
from m2v.materials.contracts import Chapter, TimeRange


def test_srt_vtt_ass_parse_to_integer_microseconds(tmp_path):
    srt = tmp_path / 'a.srt'
    srt.write_text('1\n00:00:01,250 --> 00:00:02,500\n城市夜景\n\n2\n00:00:03,000 --> 00:00:04,000\n<font>第二句</font>\n',
                   encoding='utf-8')
    parsed = parse_captions(srt, duration_us=10_000_000)
    assert [(cue.range.startUs, cue.range.endUs) for cue in parsed.cues] == [(1_250_000, 2_500_000), (3_000_000, 4_000_000)]
    assert parsed.cues[1].text == '第二句' and parsed.language == 'zh'

    vtt = tmp_path / 'b.vtt'
    vtt.write_text('WEBVTT\n\nNOTE ignore\n\ncue-1\n00:00:00.500 --> 00:00:01.000 align:start\nHello <c>world</c>\n',
                   encoding='utf-8')
    parsed = parse_captions(vtt, duration_us=2_000_000)
    assert parsed.format == 'vtt' and parsed.cues[0].text == 'Hello world' and parsed.language == 'en'

    ass = tmp_path / 'c.ass'
    ass.write_text('[Script Info]\nTitle: x\n[Events]\n'
                   'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
                   'Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,{\\fad}中英混排 text\\N换行\n',
                   encoding='utf-8')
    parsed = parse_captions(ass, duration_us=3_000_000)
    assert parsed.format == 'ass' and parsed.cues[0].range.startUs == 1_000_000
    assert '中英混排' in parsed.cues[0].text and parsed.language == 'mixed'


def test_overlap_out_of_range_and_invalid_cues_are_explicit(tmp_path):
    path = tmp_path / 'edge.vtt'
    path.write_text('WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nA\n\n'
                    '00:00:02.000 --> 00:00:05.000\nB\n\n'
                    '00:00:09.500 --> 00:00:10.400\nC\n\n'
                    '00:00:12.000 --> 00:00:13.000\nD\n\n'
                    '00:00:05.000 --> 00:00:04.000\nE\n',
                    encoding='utf-8')
    parsed = parse_captions(path, duration_us=10_000_000)
    assert [cue.text for cue in parsed.cues] == ['A', 'B', 'C']
    assert parsed.cues[-1].range.endUs == 10_000_000
    notes = ' '.join(parsed.limitations)
    assert '截断' in notes and '越界' in notes and '重叠' in notes


def test_empty_and_mixed_language_are_not_claimed_as_aligned(tmp_path):
    empty = tmp_path / 'empty.srt'
    empty.write_text('', encoding='utf-8')
    parsed = parse_captions(empty, duration_us=1_000_000)
    assert parsed.cues == [] and any('未解析到有效字幕' in note for note in parsed.limitations)
    assert language_of(['hello world', '这是中文句子']) == 'mixed'
    assert language_of([]) is None


def test_cue_ids_are_stable_and_track_scoped():
    from m2v.materials.captions import Cue
    cues = [Cue(TimeRange(startUs=0, endUs=1_000_000), '同一句')]
    first = cue_records(cues, language='zh', origin='captions-manual', source_key='track-a')
    again = cue_records(cues, language='zh', origin='captions-manual', source_key='track-a')
    other = cue_records(cues, language='zh', origin='captions-manual', source_key='track-b')
    assert first == again and first[0]['id'] != other[0]['id']


def test_chapters_map_to_records_with_origin():
    records = chapters_to_records([Chapter(title='第一章', localRange=TimeRange(startUs=0, endUs=5_000_000))])
    assert records[0]['channel'] == 'chapters' and records[0]['text'] == '第一章'
    assert records[0]['origin'] == 'source-chapters'
