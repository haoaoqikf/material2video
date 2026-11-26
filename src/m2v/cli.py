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
from m2v.type_system import registry
from m2v.type_system import catalog


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
    from m2v.types.scene_film.adapter import make_type
    for name in catalog.catalog().names():
        registry.register(make_type(name))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v", description="五类视频统一制作工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("types", help="列出内置视频类型")
    from m2v.production.cli import add_parsers
    add_parsers(sub)
    from m2v.production.sample_cli import add_parser as add_sample_parser
    add_sample_parser(sub)
    from m2v.production.video_storage import add_parser as add_storage_parser
    add_storage_parser(sub)
    voices = sub.add_parser("voices", help="列出合成可用音色（edge-tts 需要联网）")
    voices.add_argument("--locale", default="zh-CN", help="区域，例如 zh-CN；--locale all 列出全部")
    voices.add_argument("--backend", choices=("edge-tts", "kokoro", "qwen3-tts"), default="edge-tts",
                        help="合成后端；kokoro/qwen3-tts 为本地音色")
    voices.add_argument("--project", help="作品目录；qwen3-tts 的克隆音色档案在作品内")
    voices.add_argument("--json", action="store_true", help="输出 JSON")
    init = sub.add_parser("init", help="初始化作品目录")
    init.add_argument("--type", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--content-root")
    for command in ("validate", "prepare", "preview", "status", "render"):
        item = sub.add_parser(command)
        item.add_argument("--project", required=True)
        if command == "status":
            item.add_argument("--history", action="store_true", help="显示完整制作事件历史")
        if command == "preview":
            item.add_argument("--limit-frames", type=int)
            item.add_argument("--start-seconds", type=float, default=0)
            item.add_argument("--end-seconds", type=float)
        if command in {"preview", "render"}:
            item.add_argument("--jobs", type=int, default=2,
                              help="进程级并行数；默认 2；内存紧张时改为 1")
        if command == "prepare":
            # 临时试听用：不改作品文件也能换音色或改节奏，省略时跟随 project.json 的 tts。
            item.add_argument("--voice", help="合成音色，例如 zh-CN-YunxiNeural 或 zf_027")
            item.add_argument("--rate", help="语速，例如 --rate=-6%%")
            item.add_argument("--backend", choices=("edge-tts", "kokoro", "qwen3-tts"),
                              help="临时覆盖作品的 TTS 后端；省略时跟随 project.json")

            item.add_argument("--pause-comma", type=float, metavar="SECONDS", help="逗号、顿号处的停顿秒数")
            item.add_argument("--pause-period", type=float, metavar="SECONDS", help="句号、问号处的停顿秒数")
            item.add_argument("--pause-paragraph", type=float, metavar="SECONDS", help="段末停顿秒数")
            item.add_argument("--head-pad", type=float, metavar="SECONDS", help="每段口播开头的静音长度")
    lookdev = sub.add_parser("lookdev", help="代表静帧、接触表与风险样片；可按时刻或区间拼图")
    lookdev.add_argument("--project", required=True)
    lookdev.add_argument("--stills", type=int, default=None, help="静帧张数，1～12；省略为 4")
    lookdev.add_argument("--sample-seconds", type=int, default=24, help="样片长度，1～600 秒，实际窗口短于全片")
    lookdev.add_argument("--still-scale", type=int, choices=(1, 2), default=1)
    lookdev.add_argument("--sheet", nargs="+", metavar="TIME",
                         help="按时刻（秒）拼一张接触表；给单个整数时全片均匀取帧，数量为 1～24")
    lookdev.add_argument("--motion", nargs="+", type=float, metavar="TIME",
                         help="区间起止秒（可加帧数），均匀取帧拼一张看转场")
    lookdev.add_argument("--det", action="store_true", help="同帧一致性自检：两次独立采集比 PSNR")
    lookdev.add_argument("--event", action="append", metavar="SCENE:EVENT",
                         help="按幕内事件取点；可重复；需同时声明 --before/--after（帧）")
    lookdev.add_argument("--before", type=int, metavar="FRAMES", help="事件前取帧数（帧）")
    lookdev.add_argument("--after", type=int, metavar="FRAMES", help="事件后取帧数（帧）")
    lookdev.add_argument("--hold", type=int, default=0, metavar="FRAMES",
                         help="结果停留结束帧相对事件后段的额外帧数")
    qa = sub.add_parser("qa", help="通用技术 QA：接触表、冻结帧、响度、claims")
    qa.add_argument("--project", required=True)

    qa.add_argument("--video", help="待检查的成片；省略时取交付目录里的 video.mp4")
    qa.add_argument("--step", type=int, default=30, help="抽样步长（帧）")
    assets = sub.add_parser("assets", help="资产审计、素材台账与候选接触表")
    assets.add_argument("workflow", choices=("audit", "report", "contact-sheet"))
    assets.add_argument("--project",
                        help="作品目录；audit/report 必填，contact-sheet 仅用于默认输出位置")
    assets.add_argument("--sources", help="report 的来源表路径；省略时取作品 SOURCES.md")
    assets.add_argument("--input", action="append", dest="inputs", metavar="FILE",
                        help="contact-sheet 的候选文件，可重复；最多一个视频")
    assets.add_argument("--times", help="contact-sheet 的视频取帧时刻（逗号分隔秒）")
    assets.add_argument("--samples", type=int, default=6, help="未给 --times 时视频的均匀采样数")
    assets.add_argument("--columns", type=int, default=3, help="contact-sheet 的列数")
    assets.add_argument("--tile-width", type=int, default=480, help="contact-sheet 的单格宽度")
    assets.add_argument("--out", help="contact-sheet 的输出 PNG；省略时按作品或输入目录")
    assets.add_argument("--json", action="store_true", help="report/contact-sheet 输出 JSON")

    ref = sub.add_parser("ref", help="获取、校验抖音参考素材并提取授权音轨")
    ref.add_argument("workflow", choices=("fetch", "verify", "audio"))
    ref.add_argument("target", help="分享文本/链接、待校验的参考素材目录，或 ref audio 的参考目录")
    ref.add_argument("--output", help="参考素材根目录；省略时为 <工作区>/refs/douyin")
    ref.add_argument("--headed", action="store_true", help="显示浏览器窗口，便于登录或完成验证")
    ref.add_argument("--cookies", help="yt-dlp 使用的 Netscape cookie 文件路径")
    ref.add_argument("--force", action="store_true", help="校验失败或需要更新时替换已有素材或音轨")
    ref.add_argument("--json", action="store_true", help="输出 JSON")
    ref.add_argument("--project", help="ref audio 的作品目录")
    ref.add_argument("--name", help="ref audio 的音频文件名（不含扩展名；默认 ref-<作品ID>）")
    ref.add_argument("--user-authorized", dest="user_authorized",
                     help="ref audio 必填：用户明确要求复用该参考作品音频的说明原文")

    author = sub.add_parser("author", help="五类作品的语义审查、候选稿与素材操作")
    author.add_argument("workflow", choices=("status", "input-review", "candidate", "adopt-candidate", "keyframes", "assets", "sounds"))
    author.add_argument("options", nargs=argparse.REMAINDER)
    data = sub.add_parser("data", help="结构化数据来源编排")
    data.add_argument("workflow", choices=("financial-plan",))
    data.add_argument("--project", required=True)
    data.add_argument("--duration-seconds", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    _register_builtins()
    args = _parser().parse_args(argv)
    try:
        return commands.dispatch(args)
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1 if args.command != "init" else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
