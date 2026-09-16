"""命令行入口。

四个薄入口脚本（validate / prepare / preview / render）都转发到这里，
参数解析、默认输出路径推导、日志配置与退出码约定集中在同一处，
避免各脚本各自漂移。路径规则本身在 `paths` 模块，见
references/paths-and-outputs.md。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import paths as paths_mod
from . import storyboard as sb
from .errors import A2VError
from .media import Media, load_media
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
    parser.add_argument(
        "--out",
        help="输出 MP4 路径；省略时按文章归属推导为 outputs/<slug>/silent.mp4，"
        "提供 --media 时为 voiced.mp4，配合 --limit-frames 时写入 previews/",
    )
    parser.add_argument("--media", help="prepare.py 生成的媒体清单；需要 --storyboard")
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
    parser.add_argument(
        "--limit-frames",
        type=int,
        help="仅渲染前 N 帧，用于快速验证链路；省略 --out 时写入 outputs/<slug>/previews/",
    )
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
    parser.add_argument("--media", help="同时校验配音清单、字幕与音轨时长")
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
    parser.add_argument("--media", help="prepare.py 生成的媒体清单")
    parser.add_argument("--storyboard", help="源分镜路径，默认网页同目录 storyboard.json")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def main_render(argv: list[str] | None = None) -> int:
    args = _build_render_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    # 分镜校验先于路径推导：脚本无效时不必先建出输出目录
    model: sb.Storyboard | None = None
    if args.storyboard:
        model = _validated_storyboard(args.storyboard)
        if model is None:
            return _EXIT_INVALID_INPUT
    elif args.media:
        logging.error("--media 需要同时提供 --storyboard")
        return _EXIT_INVALID_INPUT

    try:
        media = load_media(args.media, args.storyboard) if args.media else None
        output = _resolve_render_output(args, model, media)
        result = render(
            page_path=args.page,
            output=output,
            storyboard=model,
            fps=args.fps,
            crf=args.crf,
            preset=args.preset,
            limit_frames=args.limit_frames,
            timeout_ms=args.timeout,
            probe=not args.no_probe,
            serve_root=args.serve_root,
            capture_format=args.capture_format,
            media=media,
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


def _validated_storyboard(path: str | Path) -> sb.Storyboard | None:
    """加载并校验分镜；有错误时打印问题并返回 None。"""
    model, report = sb.load(path)
    if model is None:
        for issue in report.errors:
            logging.error("%s", issue.format())
        logging.error("分镜脚本校验未通过，已终止渲染")
        return None
    for issue in report.warnings:
        logging.warning("%s", issue.format())
    return model


def _resolve_render_output(
    args: argparse.Namespace, model: sb.Storyboard | None, media: Media | None
) -> Path:
    """确定成片路径：显式 --out 优先，否则按文章归属推导。

    推导需要分镜：它决定成品是 silent 还是 voiced。因此省略 --out 且缺少
    --storyboard 时明确报错，而不是猜测文件名。
    """
    if args.out:
        return Path(args.out)
    try:
        article = paths_mod.for_page(args.page)
    except A2VError as exc:
        raise A2VError(f"无法推导默认输出路径，请显式指定 --out：{exc}") from exc
    if model is None:
        raise A2VError(
            "无法推导默认输出路径：省略 --out 时必须提供 --storyboard 以确定文件名，"
            "或显式指定 --out"
        )

    if media is not None:
        # 清单与音轨是同一篇文章的产物：--storyboard 决定归属，
        # --media 必须正是该文章 media/ 下的清单，否则拒绝跨文章合成。
        media_article = paths_mod.for_storyboard(args.storyboard)
        if media_article.source_dir != article.source_dir:
            raise A2VError(
                f"分镜属于 {media_article.source_dir}，与网页所属的 {article.source_dir} "
                "不是同一篇文章，拒绝跨文章合成"
            )
        if media.path.parent != media_article.media_dir.resolve():
            raise A2VError(
                f"媒体清单 {media.path} 不在 {media_article.media_dir} 内，"
                "无法确认它与本篇文章同源，拒绝合成"
            )

    voiced = paths_mod.use_voiced_name(paths_mod.declares_narration(model), media is not None)
    output = article.render_output(voiced=voiced, preview=args.limit_frames is not None)
    logging.info("未指定 --out，输出到 %s", output)
    return output


def main_validate(argv: list[str] | None = None) -> int:
    args = _build_validate_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    path = Path(args.path)
    if not path.exists():
        logging.error("文件不存在: %s", path)
        return _EXIT_INVALID_INPUT

    model, report = sb.load(path)
    if args.media and model is not None:
        try:
            model = load_media(args.media, path).storyboard
        except (A2VError, OSError) as exc:
            report.error("media", str(exc))
            model = None
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

    from .media import media_url
    from .render import _default_serve_root
    media_server = None
    try:
        media = load_media(args.media, args.storyboard or page.parent / "storyboard.json") if args.media else None
        if media:
            media_server = LocalServer(media.path.parent, cors=True)
    except (A2VError, OSError) as exc:
        logging.error("预览失败: %s", exc)
        return _EXIT_INVALID_INPUT
    server = LocalServer(_default_serve_root(page), port=args.port)
    try:
        from urllib.parse import quote
        url = f"{server.start()}/{quote(page.relative_to(server.root).as_posix())}"
        if media_server:
            url = media_url(url, media_server.start(), media)
    except OSError as exc:
        server.close()
        if media_server:
            media_server.close()
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
        if media_server:
            media_server.close()
    return _EXIT_OK


def main_prepare(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按 narration 生成配音与逐句字幕")
    parser.add_argument("--storyboard", required=True, help="分镜 JSON 路径，决定文章归属")
    parser.add_argument(
        "--out-dir",
        help="媒体输出目录；省略时按文章归属推导为 outputs/<slug>/media",
    )
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+0%", help="语速，例如 --rate=-10%%")
    parser.add_argument("--force", action="store_true", help="强制重新合成所有非空口播")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)
    from .prepare import prepare
    try:
        article = paths_mod.for_storyboard(args.storyboard)
        # Path 会折叠 "./" 之类的写法，先归一化再和推导结果比较
        out_dir = Path(args.out_dir).resolve() if args.out_dir else _default_media_dir(article)
        _reject_foreign_media_dir(article, out_dir)
        print(prepare(args.storyboard, out_dir, args.voice, args.rate, args.force))
    except (A2VError, OSError, ValueError) as exc:
        logging.error("配音准备失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("配音准备被用户中断")
        return _EXIT_FAILED
    return _EXIT_OK


def _default_media_dir(article: paths_mod.ArticlePaths) -> Path:
    """配音准备的默认输出目录：`outputs/<slug>/media`。"""
    logging.info("未指定 --out-dir，写入 %s", article.media_dir)
    return article.media_dir


def _reject_foreign_media_dir(article: paths_mod.ArticlePaths, out_dir: str | Path) -> None:
    """拒绝把媒体写进 outputs/ 下另一篇文章的目录。

    项目外的临时目录（测试、调试）仍然允许；只有明确落在 outputs/<别的 slug>/media
    时才判为冲突，避免清单和音轨被写进别人的产物目录；当前文章自己的
    outputs/<slug>/media 始终合法。
    """
    resolved = Path(out_dir).resolve()
    if resolved == article.media_dir:
        return
    outputs_root = (article.root / paths_mod.OUTPUTS_DIR).resolve()
    try:
        relative = resolved.relative_to(outputs_root)
    except ValueError:
        return
    if len(relative.parts) >= 2 and relative.parts[-1] == paths_mod.MEDIA_DIR:
        raise A2VError(
            f"--out-dir {resolved} 属于其他文章的媒体目录，本篇文章应使用 {article.media_dir}"
        )
