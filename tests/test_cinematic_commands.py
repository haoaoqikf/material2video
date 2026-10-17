"""cinematic 三个入口（lookdev / qa / assets audit）的 CLI 接线与类型守卫。"""
from __future__ import annotations

import pytest

from m2v import cli
from m2v.engine import assets_audit, lookdev, qa


def test_new_commands_are_registered():
    parser = cli._parser()
    for argv in (["lookdev", "--project", "x"], ["qa", "--project", "x"],
                 ["assets", "audit", "--project", "x"]):
        args = parser.parse_args(argv)
        assert args.project == "x"
    assert parser.parse_args(["assets", "audit", "--project", "x"]).workflow == "audit"


@pytest.mark.parametrize("argv", [["lookdev"], ["qa"], ["assets", "audit"]])
def test_new_commands_reject_non_general_projects(monkeypatch, tmp_path, argv):
    """三个入口都只服务 general：金融与住宅作品要拿到明确的话，而不是难懂的失败。"""
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
