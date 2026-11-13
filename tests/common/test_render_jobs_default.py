"""渲染并行默认值：默认 2，显式 1 仍走单会话。"""
from m2v.cli import _parser


def test_render_and_preview_default_to_two_jobs():
    for command in ("render", "preview"):
        args = _parser().parse_args([command, "--project", "demo"])
        assert args.jobs == 2, command


def test_explicit_single_job_is_kept():
    args = _parser().parse_args(["render", "--project", "demo", "--jobs", "1"])
    assert args.jobs == 1
