"""命令行入口。

`render.py` 与 `validate.py` 两个薄入口都转发到这里，参数解析、日志配置
与退出码约定集中在同一处，避免两个脚本各自漂移。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import storyboard as sb
from .errors import A2VError
from .render import render
from .static_server import LocalServer

_EXIT_OK = 0
_EXIT_FAILED = 1
_EXIT_INVALID_INPUT = 2


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def _force_utf8_output() -> None:
    """把标准输出切到 UTF-8。

    项目面向中文内容，而 Windows 控制台默认使用本地代码页（如 cp936），
    Python 按该编码写出后会被终端按 UTF-8 解读成乱码。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            # 流已被重定向且不支持重配置时忽略，不影响主流程
            pass


def _build_render_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render.py",
        description="把实现 __A2V__ 契约的动画网页逐帧渲染为 MP4",
    )
    parser.add_argument("--page", required=True, help="动画网页路径或 http(s) URL")
    parser.add_argument("--out", required=True, help="输出 MP4 路径")
    parser.add_argument(
        "--storyboard",
        help="分镜 JSON 路径；提供后与网页契约交叉校验帧率、总帧数与画面尺寸",
    )
    parser.add_argument("--fps", type=int, help="期望帧率，用于与网页契约核对")
    parser.add_argument("--crf", type=int, default=18, help="H.264 质量，越小越清晰（默认 18）")
    parser.add_argument(
        "--preset",
        default="medium",
        choices=["ultrafast", "veryfast", "fast", "medium", "slow", "slower"],
        help="x264 编码预设（默认 medium）",
    )
    parser.add_argument("--limit-frames", type=int, help="仅渲染前 N 帧，用于快速验证链路")
    parser.add_argument(
        "--capture-format",
        default="jpeg",
        choices=["jpeg", "png"],
        help="中间帧格式；jpeg 快约 3 倍，png 用于逐像素比对（默认 jpeg）",
    )
    parser.add_argument(
        "--serve-root",
        help="本地网页的静态根目录，默认取网页所在目录；资产在上一级时使用",
    )
    parser.add_argument("--timeout", type=int, default=30000, help="页面加载超时毫秒数")
    parser.add_argument("--no-probe", action="store_true", help="跳过成片解码验收")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def _build_validate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="校验分镜 JSON 的结构与时长，输出可定位的问题清单",
    )
    parser.add_argument("path", help="分镜 JSON 路径")
    parser.add_argument("--strict", action="store_true", help="把警告视为错误")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，便于程序化处理")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def _build_preview_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preview.py",
        description="以本地 HTTP 服务预览动画网页（file:// 下无法加载分镜 JSON）",
    )
    parser.add_argument("directory", nargs="?", default=".", help="静态根目录，默认当前目录")
    parser.add_argument("--page", default="index.html", help="相对根目录的页面路径")
    parser.add_argument("--port", type=int, default=0, help="监听端口，默认自动分配")
    parser.add_argument("--no-browser", action="store_true", help="只启动服务，不打开浏览器")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def main_render(argv: list[str] | None = None) -> int:
    args = _build_render_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    model: sb.Storyboard | None = None
    if args.storyboard:
        model, report = sb.load(args.storyboard)
        if model is None:
            for issue in report.errors:
                logging.error("%s", issue.format())
            logging.error("分镜脚本校验未通过，已终止渲染")
            return _EXIT_INVALID_INPUT
        for issue in report.warnings:
            logging.warning("%s", issue.format())

    try:
        result = render(
            page_path=args.page,
            output=args.out,
            storyboard=model,
            fps=args.fps,
            crf=args.crf,
            preset=args.preset,
            limit_frames=args.limit_frames,
            timeout_ms=args.timeout,
            probe=not args.no_probe,
            serve_root=args.serve_root,
            capture_format=args.capture_format,
        )
    except (A2VError, OSError) as exc:
        logging.error("渲染失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("渲染被用户中断")
        return _EXIT_FAILED

    if model is None:
        logging.info(
            "未提供分镜脚本，按网页契约渲染；总时长 %.1fs",
            result.duration_seconds,
        )
    print(result.summary())
    return _EXIT_OK


def main_validate(argv: list[str] | None = None) -> int:
    args = _build_validate_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    path = Path(args.path)
    if not path.exists():
        logging.error("文件不存在: %s", path)
        return _EXIT_INVALID_INPUT

    model, report = sb.load(path)
    if args.json:
        payload = report.to_json()
        if model is not None:
            payload["summary"] = {
                "title": model.title,
                "fps": model.fps,
                "width": model.width,
                "height": model.height,
                "sceneCount": len(model.scenes),
                "totalFrames": model.total_frames,
                "durationSeconds": round(model.total_frames / model.fps, 2),
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for issue in report.issues:
            print(issue.format(), file=sys.stderr)
        if model is not None:
            print(
                f"校验通过：{len(model.scenes)} 个场景，"
                f"{model.total_frames} 帧（{model.total_frames / model.fps:.1f}s），"
                f"{model.width}x{model.height} @{model.fps}fps"
            )

    if not report.ok or (args.strict and report.warnings):
        return _EXIT_INVALID_INPUT
    return _EXIT_OK


def main_preview(argv: list[str] | None = None) -> int:
    import time
    import webbrowser

    args = _build_preview_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    root = Path(args.directory).resolve()
    if not root.is_dir():
        logging.error("目录不存在: %s", root)
        return _EXIT_INVALID_INPUT

    page = root / args.page
    if not page.is_file():
        logging.error("页面不存在: %s", page)
        return _EXIT_INVALID_INPUT

    server = LocalServer(root, port=args.port)
    try:
        url = f"{server.start()}/{args.page.lstrip('/')}"
    except OSError as exc:
        logging.error("无法监听端口: %s", exc)
        return _EXIT_FAILED

    print(f"预览地址: {url}")
    print("按 Ctrl+C 结束预览。")
    if not args.no_browser:
        webbrowser.open(url)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
    finally:
        server.close()
    return _EXIT_OK
