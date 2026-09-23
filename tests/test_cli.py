"""CLI 与渲染辅助函数的单元测试（不启动浏览器）。"""

from __future__ import annotations

import json
from types import SimpleNamespace

from a2v import cli
from a2v.render import _last_int


class TestValidateCommand:
    def test_exit_ok_for_valid_example(self):
        from conftest import EXAMPLES_DIR

        assert cli.main_validate([str(EXAMPLES_DIR / "storyboard.json")]) == 0

    def test_exit_failed_for_missing_file(self, tmp_path):
        assert cli.main_validate([str(tmp_path / "absent.json")]) == 2

    def test_exit_failed_for_invalid_script(self, tmp_path, valid_script, capsys):
        valid_script["scenes"] = []
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        assert cli.main_validate([str(path)]) == 2

    def test_json_output_contains_summary(self, tmp_path, valid_script, capsys):
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        assert cli.main_validate([str(path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["summary"]["totalFrames"] == 90
        assert payload["summary"]["sceneCount"] == 2

    def test_directing_render_gate_requires_review_publish_conclusion(self, tmp_path, valid_script):
        valid_script["directingVersion"] = 1
        storyboard = tmp_path / "storyboard.json"
        storyboard.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        inspect_dir = tmp_path / "inspect"
        inspect_dir.mkdir()
        (inspect_dir / "report.json").write_text(json.dumps({"aestheticReview": {"findings": []}}), encoding="utf-8")
        (inspect_dir / "review.md").write_text("- 是否值得发布：待评审\n", encoding="utf-8")
        model = SimpleNamespace()
        article = SimpleNamespace(output_dir=tmp_path)
        assert "尚未填写" in cli._aesthetic_render_gate(storyboard, model, article)

    def test_json_output_lists_errors(self, tmp_path, valid_script, capsys):
        valid_script["scenes"][0]["durationInFrames"] = 0
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        assert cli.main_validate([str(path), "--json"]) == 2
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False
        assert any("durationInFrames" in item["path"] for item in payload["errors"])

    def test_strict_mode_promotes_warnings(self, tmp_path, valid_script):
        valid_script["fps"] = 29
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        assert cli.main_validate([str(path)]) == 0
        assert cli.main_validate([str(path), "--strict"]) == 2


class TestFfmpegStatsParsing:
    def test_parses_frame_count_with_padding(self):
        # ffmpeg 的行内统计在等号后有空格，按空白切分会解析失败
        stats = "frame=  120 fps= 30 q=-1.0 Lsize=N/A time=00:00:04.00 bitrate=N/A"
        assert _last_int(stats, "frame=") == 120

    def test_returns_last_occurrence(self):
        stats = "frame= 10 fps=0\nframe= 250 fps=30"
        assert _last_int(stats, "frame=") == 250

    def test_returns_none_when_absent(self):
        assert _last_int("no stats here", "frame=") is None
