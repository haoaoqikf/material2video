"""Unified ``m2v`` command line entry point.

这里只做三件事：UTF-8 输出、内置类型注册、参数解析与错误到退出码的映射。各命令的
实现见 :mod:`m2v.commands`；两者分开是因为命令实现各自加载作品、取适配器并打印结果，
与「解析 + 分发」是两件独立的事。
"""
from __future__ import annotations

import argparse
import sys

from m2v import commands
from m2v.core.errors import M2VError
from m2v.core.workspace import CONTENT_ROOT_ENV
from m2v.types import registry


def _force_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        configure = getattr(stream, "reconfigure", None)
        if configure:
            try:
                configure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _register_builtins() -> None:
    if registry.all_types():
        return
    from m2v.types.financial.adapter import TYPE as financial
    from m2v.types.general.adapter import TYPE as general
    from m2v.types.housing.adapter import TYPE as housing
    for item in (financial, general, housing):
        registry.register(item)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v", description="专用与通用视频制作工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("types", help="列出内置视频类型")
    voices = sub.add_parser("voices", help="列出合成可用音色（需要联网）")
    voices.add_argument("--locale", default="zh-CN", help="区域，例如 zh-CN；--locale all 列出全部")
    voices.add_argument("--json", action="store_true", help="输出 JSON")
    init = sub.add_parser("init", help="初始化作品目录")
    init.add_argument("--type", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--content-root")
    for command in ("validate", "prepare", "preview", "review-template", "review", "status", "render"):
        item = sub.add_parser(command)
        item.add_argument("--project", required=True)
        if command == "preview":
            item.add_argument("--limit-frames", type=int)
            item.add_argument("--start-seconds", type=float, default=0)
            item.add_argument("--end-seconds", type=float)
        if command == "prepare":
            # 临时试听用：不改作品文件也能换音色或改节奏，省略时跟随 project.json 的 tts。
            item.add_argument("--voice", help="合成音色，例如 zh-CN-YunxiNeural")
            item.add_argument("--rate", help="语速，例如 --rate=-6%%")

            item.add_argument("--pause-comma", type=float, metavar="SECONDS", help="逗号、顿号处的停顿秒数")
            item.add_argument("--pause-period", type=float, metavar="SECONDS", help="句号、问号处的停顿秒数")
            item.add_argument("--pause-paragraph", type=float, metavar="SECONDS", help="段末停顿秒数")
            item.add_argument("--head-pad", type=float, metavar="SECONDS", help="每段口播开头的静音长度")
    lookdev = sub.add_parser("lookdev", help="代表静帧、接触表与风险样片")
    lookdev.add_argument("--project", required=True)
    lookdev.add_argument("--stills", type=int, default=4, help="静帧张数，1～12")
    lookdev.add_argument("--sample-seconds", type=int, default=24, help="样片长度，1～600 秒，实际窗口短于全片")
    lookdev.add_argument("--still-scale", type=int, choices=(1, 2), default=1)
    qa = sub.add_parser("qa", help="通用技术 QA：接触表、冻结帧、响度、claims")
    qa.add_argument("--project", required=True)

    qa.add_argument("--video", help="待检查的成片；省略时取交付目录里的 video.mp4")
    qa.add_argument("--step", type=int, default=30, help="抽样步长（帧）")
    assets = sub.add_parser("assets", help="资产质量与许可审计")
    assets.add_argument("workflow", choices=("audit",))
    assets.add_argument("--project", required=True)

    ref = sub.add_parser("ref", help="获取并校验抖音参考素材")
    ref.add_argument("workflow", choices=("fetch", "verify"))
    ref.add_argument("target", help="分享文本/链接，或待校验的参考素材目录")
    ref.add_argument("--output", help="参考素材根目录；省略时为 <工作区>/refs/douyin")
    ref.add_argument("--headed", action="store_true", help="显示浏览器窗口，便于登录或完成验证")
    ref.add_argument("--force", action="store_true", help="校验失败或需要更新时替换已有素材")
    ref.add_argument("--json", action="store_true", help="输出 JSON")

    migrate = sub.add_parser("migrate", help="显式迁移已有作品并先创建完整备份")
    migrate.add_argument("--project", required=True)
    migrate.add_argument("--from", dest="source_format", required=True, choices=("financial",))
    relocate = sub.add_parser("relocate", help="将单个作品移动到按视频类型分层的标准目录")
    relocate.add_argument("--project", required=True, help="旧的 videos/<slug> 作品目录")
    relocate.add_argument("--content-root", help=f"工作区根；省略时取 {CONTENT_ROOT_ENV} 或仓库根")
    general = sub.add_parser("general", help="通用类型的语义审查、候选稿与媒体素材操作")
    general.add_argument("workflow", choices=("status", "template", "input-review", "candidate", "adopt-candidate", "keyframes", "assets"))
    general.add_argument("options", nargs=argparse.REMAINDER)
    financial = sub.add_parser("financial", help="金融类型离线材料编排工具")
    financial.add_argument("workflow", choices=("plan", "migrate-line"))
    financial.add_argument("--project", required=True)
    financial.add_argument("--duration-seconds", type=int, help="未指定时所有展示跨度均默认 60 秒")
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    _register_builtins()
    args = _parser().parse_args(argv)
    try:
        return commands.dispatch(args)
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1 if args.command not in {"init", "migrate", "relocate"} else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
