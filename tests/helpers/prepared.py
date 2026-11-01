"""跨类型测试共用的准备记录桩。"""
from __future__ import annotations


def prepared_stub(**overrides):
    prepared = {"preparedFingerprint": "x" * 8, "fps": 60, "durationInFrames": 120,
                "props": {"subtitle": {"textColor": "#ffffff", "plateColor": "#0b0d12"},
                          "compiledScenes": []},
                "audio": {"segments": [{"path": "outputs/media/master.wav"}]}}
    prepared.update(overrides)
    return prepared
