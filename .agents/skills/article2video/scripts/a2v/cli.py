"""命令行入口。

四个薄入口脚本（validate / prepare / preview / render）都转发到这里，
参数解析、默认输出路径推导、日志配置与退出码约定集中在同一处，
避免各脚本各自漂移。路径规则本身在 `paths` 模块，见
references/paths-and-outputs.md。
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import sys
from pathlib import Path

from . import fonts as fonts_mod
from . import paths as paths_mod
from . import storyboard as sb
from .errors import A2VError
from .media import Media, load_media
from .render import provenance_status, render
from .static_server import LocalServer
from .storyboard import Report

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
    parser.add_argument("--page", help="动画网页路径或 http(s) URL；省略时用共享页面读取 --storyboard")
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
    parser.add_argument("--declarative", action="store_true", help="按共享页面的受控字段规则校验")
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
    parser.add_argument("--declarative", action="store_true", help="用共享页面预览 --storyboard")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def _build_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review.py",
        description="视觉体检：抽帧量测 + 组件契约探针 + 设计宪法静态检查，并给出人工评审清单",
    )
    parser.add_argument(
        "--page",
        help="动画网页路径或 http(s) URL；省略时用共享页面读取 --storyboard",
    )
    parser.add_argument("--storyboard", required=True, help="分镜 JSON 路径，决定场景与声明")
    parser.add_argument("--media", help="配音媒体清单；提供后按真实时长抽帧")
    parser.add_argument("--out-dir", help="体检产物目录；省略时写入 outputs/<slug>/inspect")
    parser.add_argument("--serve-root", help="本地网页的静态根目录，默认取项目根")
    parser.add_argument("--timeout", type=int, default=30000, help="页面加载超时毫秒数")
    parser.add_argument(
        "--declarative", action="store_true", help="按共享页面的受控字段规则体检"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def main_render(argv: list[str] | None = None) -> int:
    args = _build_render_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)
    declarative = args.page is None
    if declarative and not args.storyboard:
        logging.error("省略 --page 时必须提供 --storyboard")
        return _EXIT_INVALID_INPUT

    # 分镜校验先于路径推导：脚本无效时不必先建出输出目录
    model: sb.Storyboard | None = None
    if args.storyboard:
        model = _validated_storyboard(args.storyboard, declarative=declarative)
        if model is None:
            return _EXIT_INVALID_INPUT
    elif args.media:
        logging.error("--media 需要同时提供 --storyboard")
        return _EXIT_INVALID_INPUT

    try:
        page = _shared_page(args.storyboard) if declarative else args.page
        source_url = _storyboard_url(args.storyboard) if declarative else None
        media = load_media(args.media, args.storyboard) if args.media else None
        output = _resolve_render_output(args, model, media)
        result = render(
            page_path=page,
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
            storyboard_url=source_url,
            storyboard_origin=args.storyboard,
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


def _validated_storyboard(path: str | Path, *, declarative: bool = False) -> sb.Storyboard | None:
    """加载并校验分镜；有错误时打印问题并返回 None。"""
    model, report = sb.load(path, declarative=declarative)
    if model is None:
        for issue in report.errors:
            logging.error("%s", issue.format())
        logging.error("分镜脚本校验未通过，已终止渲染")
        return None
    for issue in report.warnings:
        logging.warning("%s", issue.format())
    return model


def _shared_page(storyboard: str | Path) -> Path:
    article = paths_mod.for_storyboard(storyboard)
    page = article.root / ".agents/skills/article2video/assets/declarative.html"
    if not page.is_file():
        raise A2VError(f"共享页面不存在: {page}")
    return page


def _storyboard_url(storyboard: str | Path) -> str:
    article = paths_mod.for_storyboard(storyboard)
    return "/" + Path(storyboard).resolve().relative_to(article.root).as_posix()


def _with_storyboard_query(url: str, storyboard: str | Path) -> str:
    """给共享页面 URL 补上 `a2v-storyboard` 查询参数。

    共享页面（`assets/declarative.html`）从该参数指定的路径加载分镜，渲染入口在
    起服务前就拼好了它；体检走的是通用的「本地页面 → URL」转换，因此在这里补上，
    否则页面会因缺少参数直接报错，探针拿不到任何场景。
    """
    from urllib.parse import quote

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}a2v-storyboard={quote(_storyboard_url(storyboard), safe='')}"


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
        article = (paths_mod.for_storyboard(args.storyboard) if args.page is None
                   else paths_mod.for_page(args.page))
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

    model, report = sb.load(path, declarative=args.declarative)
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

    if args.declarative:
        if not args.storyboard or _validated_storyboard(args.storyboard, declarative=True) is None:
            logging.error("声明式预览需要有效的 --storyboard")
            return _EXIT_INVALID_INPUT
        try:
            page = _shared_page(args.storyboard)
            source_url = _storyboard_url(args.storyboard)
        except A2VError as exc:
            logging.error("预览失败: %s", exc)
            return _EXIT_INVALID_INPUT
    else:
        root = Path(args.directory).resolve()
        if not root.is_dir():
            logging.error("目录不存在: %s", root)
            return _EXIT_INVALID_INPUT
        page = root / args.page
        if not page.is_file():
            logging.error("页面不存在: %s", page)
            return _EXIT_INVALID_INPUT
        source_url = None

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
        if source_url:
            from urllib.parse import urlencode
            url += "?" + urlencode({"a2v-storyboard": source_url})
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


def main_review(argv: list[str] | None = None) -> int:
    """视觉评审：一次跑完静态宪法、帧量测与组件契约探针。"""
    args = _build_review_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    from . import inspect as inspect_mod
    from . import storyboard as sb
    from .browser import open_animated_page
    from .media import load_media, media_url
    from .render import _default_serve_root, _resolve_page_url

    declarative = args.page is None
    if declarative:
        try:
            args.page = str(_shared_page(args.storyboard))
        except A2VError as exc:
            logging.error("声明式体检需要有效的 --storyboard：%s", exc)
            return _EXIT_INVALID_INPUT

    model, report = sb.load(args.storyboard, declarative=declarative)
    if model is None or not report.ok:
        for issue in report.issues:
            logging.error("%s", issue.format())
        logging.error("分镜脚本校验未通过，无法体检")
        return _EXIT_INVALID_INPUT

    try:
        media = load_media(args.media, args.storyboard) if args.media else None
        scenes = inspect_mod.scenes_as_dicts(media.storyboard if media else model)
    except (A2VError, OSError) as exc:
        logging.error("体检失败: %s", exc)
        return _EXIT_FAILED

    page_file = Path(args.page)
    if not declarative and not page_file.is_file():
        logging.error(
            "网页文件不存在: %s；共享页面请改用 --declarative（省略 --page）", page_file
        )
        return _EXIT_INVALID_INPUT
    out_dir = Path(args.out_dir) if args.out_dir else _default_review_dir(args.page, args.storyboard)
    # 静态宪法先跑：它最便宜，而且网页结构不对时抽帧也白搭
    combined = Report()
    for issue in inspect_mod.check_page_with_storyboard(
        page_file, scenes, runtime_scenes=declarative
    ).issues:
        combined.add(issue.level, issue.path, issue.message)

    try:
        with contextlib.ExitStack() as stack:
            url = stack.enter_context(_resolve_page_url(page_file, args.serve_root))
            if declarative:
                url = _with_storyboard_query(url, args.storyboard)
            if media:
                media_server = stack.enter_context(LocalServer(media.path.parent, cors=True))
                url = media_url(url, media_server.base_url, media)
            with open_animated_page(
                url, timeout_ms=args.timeout, width=model.width, height=model.height
            ) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                preset = str(((media.storyboard if media else model).visual or {}).get("preset") or "")
                page_report, extra = inspect_mod.run_inspect(
                    page, scenes, out_dir / "frames", out_dir, preset=preset
                )
    except (A2VError, OSError, ValueError) as exc:
        logging.error("体检失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("体检被用户中断")
        return _EXIT_FAILED

    for issue in page_report.issues:
        combined.add(issue.level, issue.path, issue.message)
    # 观感闸门默认只提示、不拦：画面能用但不够发布会级，最终判断归人。
    # 但**溢出**是例外——文字被裁掉或压出安全区属于画面坏了，与「不是废片」
    # 同类。它必须影响错误数与退出码，否则闸门报了失败而 CI 看到的是 0 个错误。
    _apply_hard_gates(combined, extra.get("keynote") or {})

    # 缺字是唯一一种静默失败：浏览器不报错、不警告，直接用系统字体顶上，
    # 字宽字重基线全变，而上面的对齐（K4）与溢出（K7）量的都是元素框、照过。
    # 它和 K7 同性质（画面坏了），所以进错误数与退出码。
    for finding in _font_findings(page_file, args):
        if finding.get("skip"):
            # 空转的检查与通过的检查在报告里长得一样——所以要把「不适用」写出来。
            combined.warn(finding["where"], finding["skip"])
            continue
        combined.error(finding["where"], "字体缺字：" + "".join(finding["missing"]))
    payload = inspect_mod.write_report(
        combined,
        {
            **extra,
            "page": str(page_file),
            "storyboard": str(args.storyboard),
            "source": "media" if media else "storyboard",
            "provenance": _rendered_provenance(out_dir),
        },
        out_dir / "report.json",
    )

    for issue in combined.issues:
        print(issue.format(), file=sys.stderr)
    print(_review_summary(payload, out_dir))
    return _EXIT_OK if combined.ok else _EXIT_INVALID_INPUT


def _default_review_dir(page: str | Path, storyboard: str | Path) -> Path:
    """体检产物目录：`outputs/<slug>/inspect`，与渲染产物放在一起。

    专属网页优先按网页归属；共享页面不在 `videos/`、`examples/` 下，
    此时回退到分镜归属，与渲染入口的推导保持一致。
    """
    try:
        article = paths_mod.for_page(page)
    except A2VError:
        article = paths_mod.for_storyboard(storyboard)
    target = article.output_dir / "inspect"
    logging.info("未指定 --out-dir，体检产物写入 %s", target)
    return target


def _font_findings(page_file: Path, args) -> list[dict]:
    """按网页实际声明的字体查缺字（`narration` 等不渲染的字段不进扫描）。"""
    import json as _json

    path = Path(args.storyboard) if args.storyboard else None
    if path is None or not path.is_file():
        return []
    try:
        storyboard = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not fonts_mod.page_fonts(page_file):
        return [{
            "where": "字体覆盖",
            "skip": "本页未声明 webfont（不启用预设时走系统字体），字体覆盖检查不适用",
        }]
    try:
        return fonts_mod.audit_page(page_file, storyboard)
    except (OSError, ValueError) as exc:
        logging.warning("字体覆盖检查跳过：%s", exc)
        return []


def _rendered_provenance(out_dir: Path) -> dict:
    """这个作品的成片是不是旧资产渲的。

    成片与体检产物同属一个作品目录（`outputs/<slug>/voiced.mp4` 对
    `outputs/<slug>/inspect/`），所以从体检目录往上一级找成片。
    它只回答「产物是不是旧的」，**不参与错误数与退出码**——
    「不够发布会级」和「这些片子不是最新资产渲的」都不是「画面坏了」。
    没有成片时返回空表，不报「无法判断」：还没渲过不是问题。
    """
    work_dir = out_dir.parent
    found: dict[str, dict] = {}
    for name in ("voiced", "silent"):
        video = work_dir / f"{name}.mp4"
        if video.is_file():
            found[name] = provenance_status(video)
    return found


def _provenance_lines(provenance: dict | None) -> list[str]:
    """成片溯源一行话：这个成片是不是旧资产渲的。

    这份结论**不改错误数、不改退出码**——它是提示，不是废片判定。
    `unknown` 要写得像 `unknown`：安静地什么都不说，和「对得上」长得一样，
    而那正是这套机检一直在消灭的失败模式。
    """
    if not provenance:
        return []
    marks = {"current": "✓", "stale": "!", "unknown": "?"}
    labels = {
        "current": "对得上",
        "stale": "落后：不是当前资产渲的，要重渲",
        "unknown": "无法判断",
    }
    lines = ["成片溯源（只提示、不拦人）："]
    for name, result in provenance.items():
        status = result.get("status", "unknown")
        lines.append(f"  {marks.get(status, '?')} {name}.mp4：{labels.get(status, status)}——{result.get('detail', '')}")
    return lines


def _review_summary(payload: dict, out_dir: Path) -> str:
    """终端摘要 + 人工评审清单。分数不给自动结论，只把该看的摆出来。"""
    lines = [
        f"体检完成：{payload['frameCount']} 帧抽检，"
        f"{payload['summary']['errors']} 个错误，{payload['summary']['warnings']} 个提醒",
        f"产物：{out_dir / 'report.json'}",
        f"联系表：{out_dir / 'contact-sheet.png'}",
    ]
    probes = payload.get("contract") or []
    if probes:
        using = payload.get("usedComponentLibrary", True)
        lines.append("组件契约：" + ("" if using else "（网页未使用组件库，已跳过）"))
        for probe in probes:
            mark = "✓" if probe["ok"] else "✗"
            kind = probe["kind"] or "（未挂载）"
            lines.append(f"  {mark} {probe['scene']}: {kind}" if using else f"  - {probe['scene']}")

    keynote = payload.get("keynote")
    if keynote is not None:
        lines.extend(_keynote_lines(keynote))

    motion_result = payload.get("motion")
    if motion_result is not None:
        lines.extend(_motion_lines(motion_result))

    lines.extend(_provenance_lines(payload.get("provenance")))

    lines.append("接下来需要人（或视觉模型）看的：见 references/visual-review-rubric.md")
    return "\n".join(lines)


#: 观感闸门里的硬判定。它们与「不是废片」类检查同性质：不通过就不该出片。
#: 其余观感闸门只提示——「不够发布会级」和「画面坏了」不是一回事。
_HARD_GATES = ("K7",)


def _apply_hard_gates(report: Report, keynote: dict) -> None:
    """把硬判定闸门的失败并入错误列表，让错误数与退出码如实反映它们。

    「观感」这层默认不拦人：留白少了、强调色淡了都是主观判断。但文字溢出不是
    主观判断——它意味着有人会看到被裁掉的半行字。只打印一条「失败」而不影响
    结论，等于把硬判定降级成了建议。
    """
    for gate in keynote.get("gates") or []:
        if gate.get("id") in _HARD_GATES and gate.get("status") == "fail":
            report.error(
                str(gate.get("scene") or "keynote"),
                f"{gate.get('title')}：{gate.get('detail')}",
            )


def _keynote_lines(keynote: dict) -> list[str]:
    """观感闸门摘要。与「不是废片」类检查分开列，不混成一个总分。"""
    if not keynote.get("enabled"):
        return [f"观感闸门 K1–K7：不适用——{keynote.get('reason') or '未启用设计语言预设'}"]
    summary = keynote.get("summary") or {}
    lines = [
        "观感闸门 K1–K7（与上面的废片类检查分开计）："
        f"{summary.get('pass', 0)} 条通过 / {summary.get('warn', 0)} 条提醒 / "
        f"{summary.get('fail', 0)} 条失败 / {summary.get('skipped', 0)} 条跳过"
    ]
    # 只列「不通过」与「跳过」的条目：通过项已在 report.json 里留有实测值
    for gate in keynote.get("gates") or []:
        if gate.get("status") == "pass":
            continue
        scope = f"[{gate.get('scene')}] " if gate.get("scene") else ""
        if gate.get("status") == "skipped":
            shown = gate.get("detail") or "无法实测"
        else:
            shown = f"实测 {gate.get('value')} / 阈值 {gate.get('threshold')}"
            # 硬判定（例如文字越界）必须说清是哪段文字、往哪个方向越了多少：
            # 只给一个数字，人无法据此改分镜。
            if gate.get("status") == "fail" and gate.get("detail"):
                shown += f"；{gate.get('detail')}"
        lines.append(f"  {scope}{gate.get('id')} {gate.get('title')}：{shown}")
    return lines


def _motion_lines(motion_result: dict) -> list[str]:
    """动效闸门摘要 M0–M4。

    与「不是废片」类检查分开列，也不并入观感闸门：那两栏回答「画面对不对」，
    这一栏回答「动作对不对」。
    """
    if not motion_result.get("enabled"):
        return [f"动效量测 M0–M4：不适用——{motion_result.get('reason') or '未启用逐帧量测'}"]
    summary = motion_result.get("summary") or {}
    lines = [
        "动效量测 M0–M4（逐帧扫过全片；只提示、不拦人）："
        f"{summary.get('pass', 0)} 条通过 / {summary.get('warn', 0)} 条提醒 / "
        f"{summary.get('fail', 0)} 条失败 / {summary.get('skipped', 0)} 条跳过"
    ]
    for gate in motion_result.get("gates") or []:
        if gate.get("status") == "pass":
            scope = f"[{gate.get('scene')}] " if gate.get("scene") else ""
            lines.append(f"  {scope}{gate.get('id')} {gate.get('title')}：{gate.get('value')}")
            continue
        scope = f"[{gate.get('scene')}] " if gate.get("scene") else ""
        shown = gate.get("detail") or gate.get("value") or "无法实测"
        lines.append(f"  {scope}{gate.get('id')} {gate.get('title')}：{shown}")
    return lines


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
    parser.add_argument(
        "--subset-fonts",
        metavar="FONT",
        help="额外切一份只含本作品用字的字体子集（需要可选依赖 uv sync --extra fonts）；"
             "源字体只读，子集落在作品目录",
    )
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
        if args.subset_fonts:
            return _subset_fonts(args.storyboard, out_dir, Path(args.subset_fonts))
    except (A2VError, OSError, ValueError) as exc:
        logging.error("配音准备失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("配音准备被用户中断")
        return _EXIT_FAILED
    return _EXIT_OK


def _subset_fonts(storyboard_path: str | Path, out_dir: Path, source: Path) -> int:
    """按本作品的用字切一份字体子集，并立刻用缺字机检判它覆盖不覆盖。

    切与判必须成对：漏字的子集会静默回退到系统字体（字宽字重基线全变），
    那正是这条能力存在的意义。源字体**只读**——共享字体要渲染将来的任意文章。
    页面引用哪份字体由生成流程决定（工具只负责切与校验）。
    """
    import json as _json

    from . import fonts as fonts_mod

    if not source.is_file():
        logging.error("源字体不存在：%s", source)
        return _EXIT_FAILED
    try:
        storyboard = _json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logging.error("分镜读不出来，无法确定字符集：%s", exc)
        return _EXIT_FAILED
    charset = fonts_mod.charset_for(storyboard)
    target = out_dir.parent / f"subset-{source.stem}.ttf"
    try:
        fonts_mod.subset_font(source, charset, target)
    except fonts_mod.SubsetUnavailable as exc:
        logging.error("切字体子集失败: %s", exc)
        return _EXIT_FAILED
    findings = fonts_mod.audit(storyboard, target)
    if findings:
        for finding in findings:
            logging.error("子集缺字：%s 缺 %s", finding["where"], "".join(finding["missing"]))
        return _EXIT_FAILED
    print(f"字体子集 {target}：{len(charset)} 个字符，{target.stat().st_size / 1024:.0f} KB；缺字检查通过")
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
