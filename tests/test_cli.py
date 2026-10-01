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

    def test_v4_validation_reports_global_stage_timeline(self, tmp_path, capsys):
        from pathlib import Path
        source = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-vectors.json").read_text(encoding="utf-8"))["valid"]
        path = tmp_path / "storyboard-v4.json"
        path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        assert cli.main_validate([str(path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["summary"]["sceneCount"] == len(source["stages"])
        assert payload["summary"]["totalFrames"] == source["stages"][0]["durationInFrames"]
        assert payload["warnings"][0]["path"] == "diversity"
        model = cli._validated_storyboard(path)
        assert model.total_frames == payload["summary"]["totalFrames"]

    def test_v4_actual_duration_blocks_final_output_with_actionable_message(self, tmp_path, monkeypatch):
        from pathlib import Path
        source = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-vectors.json").read_text(encoding="utf-8"))["valid"]
        path = tmp_path / "storyboard-v4.json"
        path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(cli, "load_media", lambda *_args: SimpleNamespace(data={
            "standardCheck": {"durationStatus": "fail", "actualDurationSeconds": 46.0},
        }))
        issue = cli._aesthetic_render_gate(path, SimpleNamespace(), None, tmp_path / "media.json")
        assert "实际全片时长 46.00 秒" in issue
        assert "重新 prepare 和评审" in issue
        assert "截断口播或补空白" in issue

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
        assert payload["summary"]["totalFrames"] == 180
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

    def test_code_scene_render_gate_requires_dynamic_review(self, tmp_path, valid_script):
        valid_script["directingVersion"] = 1
        valid_script["scenes"][0]["renderer"] = {"kind": "code", "module": "example"}
        storyboard = tmp_path / "storyboard.json"
        storyboard.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
        inspect_dir = tmp_path / "inspect"
        inspect_dir.mkdir()
        (inspect_dir / "report.json").write_text(json.dumps({
            "aestheticReview": {"findings": []},
            "bespokeAnimationReview": {"required": True, "status": "待评审", "publishable": False},
        }), encoding="utf-8")
        (inspect_dir / "review.md").write_text("- 是否值得发布：通过\n", encoding="utf-8")
        article = SimpleNamespace(output_dir=tmp_path)
        assert cli._aesthetic_render_gate(storyboard, SimpleNamespace(), article) == "定制动画动态评审待评审"

    def test_final_render_rejects_partial_global_frame_range(self, tmp_path, monkeypatch):
        cli._force_utf8_output = lambda: None
        monkeypatch.setattr(cli, "_validated_storyboard", lambda *_args: SimpleNamespace(total_frames=90))
        monkeypatch.setattr(cli, "_article_for", lambda *_args, **_kwargs: SimpleNamespace(preview_dir=tmp_path))
        result = cli.main_render(["--storyboard", "storyboard.json", "--purpose", "final",
                                  "--frame-range", "10-20", "--out", str(tmp_path / "out.mp4")])
        assert result != 0

    def test_review_render_requires_preview_directory(self, tmp_path, monkeypatch):
        cli._force_utf8_output = lambda: None
        monkeypatch.setattr(cli, "_validated_storyboard", lambda *_args: SimpleNamespace(total_frames=90))
        monkeypatch.setattr(cli, "_article_for", lambda *_args, **_kwargs: SimpleNamespace(preview_dir=tmp_path / "previews"))
        result = cli.main_render(["--storyboard", "storyboard.json", "--purpose", "review",
                                  "--out", str(tmp_path / "final.mp4")])
        assert result != 0

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

    def test_prepare_stops_before_tts_when_input_review_is_missing(self, tmp_path, monkeypatch, caplog):
        from a2v import prepare as prepare_module

        article = SimpleNamespace(kind="article", source_dir=tmp_path, workspace_root=tmp_path,
                                  output_dir=tmp_path / "outputs", media_dir=tmp_path / "outputs" / "media")
        called = []
        cli._force_utf8_output = lambda: None
        monkeypatch.setattr(cli.paths_mod, "for_storyboard", lambda *_args, **_kwargs: article)
        monkeypatch.setattr(cli, "_reject_foreign_media_dir", lambda *_args: None)
        monkeypatch.setattr(prepare_module, "prepare", lambda *args: called.append(args))
        result = cli.main_prepare(["--storyboard", str(tmp_path / "storyboard.json")])
        assert result == 1
        assert called == []
        assert "缺少输入审查记录" in caplog.text


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
