"""cinematic 三个入口（lookdev / qa / assets audit）的 CLI 接线与类型守卫。"""
from __future__ import annotations

import pytest

from m2v import cli
from m2v.core.errors import M2VError
from m2v.engine import assets_audit, lookdev, qa


def test_new_commands_are_registered():
    parser = cli._parser()
    for argv in (["lookdev", "--project", "x"], ["qa", "--project", "x"],
                 ["assets", "audit", "--project", "x"],
                 ["assets", "report", "--project", "x"],
                 ["assets", "contact-sheet", "--input", "a.mp4"]):
        args = parser.parse_args(argv)
        assert args.project == "x" or args.workflow == "contact-sheet"
    assert parser.parse_args(["assets", "audit", "--project", "x"]).workflow == "audit"
    assert parser.parse_args(["assets", "report", "--project", "x"]).workflow == "report"
    sheet = parser.parse_args(["assets", "contact-sheet", "--input", "a.mp4",
                               "--times", "0,2", "--columns", "2"])
    assert (sheet.workflow, sheet.inputs, sheet.times, sheet.columns) == (
        "contact-sheet", ["a.mp4"], "0,2", 2)


def test_assets_report_forwards_options(monkeypatch):
    """report 把来源表与 JSON 开关原样交给实现，不自行改写参数。"""
    import m2v.engine.assets_tools as tools
    from m2v import commands

    captured = {}

    def fake_report_main(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(tools, "report_main", fake_report_main)
    args = cli._parser().parse_args(["assets", "report", "--project", "x",
                                     "--sources", "s.md", "--json"])
    assert commands.dispatch(args) == 0
    assert captured == {"project": "x", "sources": "s.md", "as_json": True}


def test_assets_contact_sheet_forwards_options(monkeypatch, tmp_path):
    import m2v.engine.assets_tools as tools
    from m2v import commands

    captured = {}

    def fake_contact_main(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(tools, "contact_main", fake_contact_main)
    args = cli._parser().parse_args(["assets", "contact-sheet", "--input", "a.png",
                                     "--input", "b.png", "--samples", "4",
                                     "--tile-width", "320", "--out", str(tmp_path / "s.png")])
    assert commands.dispatch(args) == 0
    assert captured["inputs"] == ["a.png", "b.png"]
    assert (captured["samples"], captured["tile_width"], captured["project"]) == (4, 320, None)


def test_assets_report_rejects_non_general_project(monkeypatch, tmp_path):
    import m2v.engine.assets_tools as tools

    manifest = {"id": "x", "type": "financial-timeseries", "materials": {}}
    monkeypatch.setattr(tools, "load_project", lambda path: (tmp_path, manifest))
    with pytest.raises(M2VError, match="仅适用于 general"):
        tools.report_main(project=str(tmp_path))


@pytest.mark.parametrize("argv", [["lookdev"], ["qa"], ["assets", "audit"]])
def test_new_commands_reject_non_general_projects(monkeypatch, tmp_path, argv):
    """三个入口都只服务 general：金融作品要拿到明确的话，而不是难懂的失败。"""
    import m2v.core.project as project_module

    manifest = {"id": "x", "type": "financial-timeseries", "materials": {}}
    fake = lambda path: (tmp_path, manifest)  # noqa: E731 - 测试替身
    # qa 在 main() 里就地导入，因此还要替换 core.project 上的那份。
    monkeypatch.setattr(project_module, "load_project", fake)
    for module in (lookdev, assets_audit):
        monkeypatch.setattr(module, "load_project", fake)
    assert cli.main([*argv, "--project", str(tmp_path)]) == 1


def test_new_commands_reject_unknown_profile(tmp_path):
    parser = cli._parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["qa", "--project", "x", "--profile", "epic"])


def test_lookdev_preview_parameters_are_registered():
    """三种取点模式的参数必须能从统一入口解析，且保持可选。"""
    parser = cli._parser()
    args = parser.parse_args(["lookdev", "--project", "x", "--sheet", "3.5", "9", "21.5"])
    assert args.sheet == ["3.5", "9", "21.5"] and args.stills is None
    args = parser.parse_args(["lookdev", "--project", "x", "--motion", "8.2", "10.6", "12"])
    assert args.motion == [8.2, 10.6, 12.0]
    args = parser.parse_args(["lookdev", "--project", "x", "--det"])
    assert args.det is True
    args = parser.parse_args(["lookdev", "--project", "x", "--event", "a:contact",
                              "--before", "6", "--after", "6", "--hold", "12"])
    assert args.event == ["a:contact"]
    assert (args.before, args.after, args.hold) == (6, 6, 12)
    # 不声明取点模式时，仍按代表静帧处理。
    assert parser.parse_args(["lookdev", "--project", "x"]).sheet is None


def test_lookdev_forwards_preview_arguments(monkeypatch):
    """取点模式的参数要原样转发；未声明 --stills 时不伪造张数。"""
    import m2v.engine.lookdev as lookdev_engine
    from m2v import commands

    captured = {}

    def fake_main(argv):
        captured["argv"] = argv
        return 0
    monkeypatch.setattr(lookdev_engine, "main", fake_main)
    args = cli._parser().parse_args(["lookdev", "--project", "x", "--sheet", "2", "8"])
    assert commands.dispatch(args) == 0
    assert captured["argv"] == ["--project", "x", "--sample-seconds", "24",
                                "--still-scale", "1", "--sheet", "2", "8"]


def test_lookdev_forwards_event_arguments(monkeypatch):
    """事件取点要把事件、前后窗口与停留帧原样转发。"""
    import m2v.engine.lookdev as lookdev_engine
    from m2v import commands

    captured = {}

    def fake_main(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(lookdev_engine, "main", fake_main)
    args = cli._parser().parse_args(["lookdev", "--project", "x", "--event", "a:contact",
                                    "--before", "6", "--after", "6", "--hold", "12"])
    assert commands.dispatch(args) == 0
    assert captured["argv"] == ["--project", "x", "--sample-seconds", "24", "--still-scale", "1",
                                "--event", "a:contact", "--before", "6", "--after", "6",
                                "--hold", "12"]
