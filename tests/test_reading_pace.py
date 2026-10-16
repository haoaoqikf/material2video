"""阅读速度报告：按字/秒量算、超限只报告不阻断。"""
from __future__ import annotations

import json

from m2v.cli import _report_reading_pace
from m2v.types.general import adapter, reading_pace

from test_article_explainer import fake_tts, project


def cue(start, end, text):
    return {"startFrame": start, "endFrame": end, "text": text}


def test_字数排除标点与空白():
    """与既有 `count_characters` 同口径：标点不计入阅读量。"""
    measured = reading_pace.entries([cue(0, 30, "观察结果，修正做法。")])
    assert len(measured) == 1
    assert measured[0]["characters"] == 8
    assert measured[0]["seconds"] == 1.0
    assert measured[0]["charactersPerSecond"] == 8.0


def test_零长与无字的字幕不参与判定():
    assert reading_pace.entries([cue(5, 5, "有字"), cue(0, 30, "，。")]) == []


def test_超限条目单独列出():
    prepared = {"preparedFingerprint": "x" * 64,
        "subtitles": [cue(0, 15, "观察结果，修正做法。"), cue(15, 60, "慢慢说清楚。")]}
    report = reading_pace.report(prepared)
    assert report["status"] == "over-limit"
    # 8 字 / 0.5 秒 = 16 字/秒，超过 9
    assert [c["charactersPerSecond"] for c in report["overLimit"]] == [16.0]
    assert report["limitPerSecond"] == 9.0
    assert report["source"]


def test_没有超限时为_pass():
    prepared = {"preparedFingerprint": "y" * 64, "subtitles": [cue(0, 30, "观察结果，修正做法。")]}
    assert reading_pace.report(prepared)["status"] == "pass"


def test_报告绑定准备指纹(tmp_path):
    prepared = {"preparedFingerprint": "z" * 64, "subtitles": [cue(0, 30, "观察结果。")]}
    payload = reading_pace.write(tmp_path, prepared)
    written = json.loads((tmp_path / reading_pace.REPORT).read_text(encoding="utf-8"))
    assert written == payload
    assert written["preparedFingerprint"] == "z" * 64


def test_超限不阻断准备并写出报告(tmp_path, monkeypatch):
    """半秒的口播配 8 个字，必然超限；准备仍应成功。"""
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, seconds=0.5)
    prepared = adapter.prepare(root, manifest)
    report = json.loads((root / reading_pace.REPORT).read_text(encoding="utf-8"))
    assert report["status"] == "over-limit"
    assert report["preparedFingerprint"] == prepared["preparedFingerprint"]


def test_cli_超限时打印提示且不抛错(tmp_path, monkeypatch, capsys):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, seconds=0.5)
    adapter.prepare(root, manifest)
    _report_reading_pace(root)
    printed = capsys.readouterr()
    assert "[warning]" in printed.err
    assert "9.0 字/秒" in printed.err


def test_cli_没有报告文件时静默(tmp_path, capsys):
    _report_reading_pace(tmp_path)
    assert capsys.readouterr().err == ""


def test_cli_报告损坏时提示而不是崩溃(tmp_path, capsys):
    (tmp_path / "outputs").mkdir()
    (tmp_path / reading_pace.REPORT).write_text("{不是 JSON", encoding="utf-8")
    _report_reading_pace(tmp_path)
    assert "无法读取" in capsys.readouterr().err
