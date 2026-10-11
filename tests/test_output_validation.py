from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from a2v.core.errors import A2VError
from a2v.engine import output_validation


def test_decoded_progress_reports_the_last_frame_count() -> None:
    assert output_validation._decoded_frame_count("frame=0\nprogress=continue\nframe=30\nprogress=end\n") == 30
    assert output_validation._decoded_frame_count("progress=end\n") is None


def test_output_validation_rejects_wrong_decoded_frame_count(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "video.mp4"
    output.write_bytes(b"video")
    monkeypatch.setattr(output_validation, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(output_validation.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout="frame=29\nprogress=end\n", stderr=""))
    with pytest.raises(A2VError, match="期望 30，实际 29"):
        output_validation.verify_output(output, 30, 1080, 1920, 30)
