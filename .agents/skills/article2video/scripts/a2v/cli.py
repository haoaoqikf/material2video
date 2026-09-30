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
from typing import Any

from . import contract_page
from . import fonts as fonts_mod
from . import paths as paths_mod
from . import storyboard as sb
from . import visual_narrative as vn
from .errors import A2VError
from .media import Media, load_media
from .render import provenance_status, render_with_remotion
from .http_server import LocalServer
from .storyboard import Report

_EXIT_OK = 0
_EXIT_FAILED = 1
_EXIT_INVALID_INPUT = 2

ENGINE_REACT = "remotion"


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


def _add_engine_argument(parser: argparse.ArgumentParser) -> None:
    """保留命令行显式引擎参数；当前唯一引擎为 Remotion composition。"""
    parser.add_argument(
        "--engine",
        choices=[ENGINE_REACT],
        default=ENGINE_REACT,
        help=(
            "画面引擎：Remotion React composition（保留参数用于明确契约）"
        ),
    )


def _build_render_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render.py",
        description="把分镜按契约页逐帧渲染为 MP4",
    )
    parser.add_argument(
        "--out",
        help="输出 MP4 路径；省略时按文章归属推导为 videos/<slug>/outputs/silent.mp4，"
        "提供 --media 时为 voiced.mp4，配合 --limit-frames 时写入 previews/",
    )
    parser.add_argument("--media", help="prepare.py 生成的媒体清单；需要 --storyboard")
    parser.add_argument(
        "--storyboard",
        help="分镜 JSON 路径；提供后与网页契约交叉校验帧率、总帧数与画面尺寸",
    )
    parser.add_argument(
        "--content-root",
        help="文章与产物所在的工作区根；省略时读环境变量 A2V_CONTENT_ROOT，"
        "两者都没有则用仓库根（文章与仓库不分离时的默认行为）",
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
        help="仅渲染前 N 帧，用于快速验证链路；省略 --out 时写入 videos/<slug>/outputs/previews/",
    )
    parser.add_argument("--frame-range", help="渲染 composition 的全局帧区间 start-end（审片输出）")
    parser.add_argument("--scale", type=float, default=1, help="输出缩放比例；仅供审片输出降低分辨率")
    parser.add_argument("--purpose", choices=("final", "review"), default="final", help="输出用途；正式成片执行完整制作闸门")
    parser.add_argument("--timeout", type=int, default=30000, help="页面加载超时毫秒数")
    parser.add_argument("--no-probe", action="store_true", help="跳过成片解码验收")
    _add_engine_argument(parser)
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
    parser.add_argument("--reference", action="append", default=[], help="显式提供跨作品多样性比较的参考分镜，可重复")
    parser.add_argument(
        "--content-root",
        help="文章所在的工作区根；分镜声明代码场景时用它解析 scenes/ 下的模块，"
        "省略时读环境变量 A2V_CONTENT_ROOT，都不设则为仓库根",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def _build_preview_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preview.py",
        description="以本地 HTTP 服务在契约页预览画面（file:// 下无法加载分镜 JSON）",
    )
    parser.add_argument("--port", type=int, default=0, help="监听端口，默认自动分配")
    parser.add_argument("--no-browser", action="store_true", help="只启动服务，不打开浏览器")
    parser.add_argument("--media", help="prepare.py 生成的媒体清单")
    parser.add_argument("--storyboard", help="源分镜路径（必需）")
    _add_engine_argument(parser)
    parser.add_argument(
        "--content-root",
        help="文章所在的工作区根；省略时读环境变量 A2V_CONTENT_ROOT，都不设则为仓库根",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def _build_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review.py",
        description="视觉体检：抽帧量测 + 契约探针 + 观感闸门，并给出人工评审清单",
    )
    parser.add_argument("--storyboard", required=True, help="分镜 JSON 路径，决定场景与声明")
    parser.add_argument(
        "--content-root",
        help="文章所在的工作区根；省略时读环境变量 A2V_CONTENT_ROOT，都不设则为仓库根",
    )
    parser.add_argument("--media", help="配音媒体清单；提供后按真实时长抽帧")
    parser.add_argument("--out-dir", help="体检产物目录；省略时写入 videos/<slug>/outputs/inspect")
    parser.add_argument("--timeout", type=int, default=30000, help="页面加载超时毫秒数")
    parser.add_argument(
        "--check-determinism",
        action="store_true",
        help="对每幕收尾帧做同帧重复截图与随机寻帧验收（PSNR ≥ 60 dB）；"
        "失败计为错误，退出码非零",
    )
    _add_engine_argument(parser)
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    return parser


def main_render(argv: list[str] | None = None) -> int:
    args = _build_render_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)
    if not args.storyboard:
        logging.error("Remotion 渲染必须提供 --storyboard")
        return _EXIT_INVALID_INPUT

    # 分镜校验先于路径推导：脚本无效时不必先建出输出目录
    model = _validated_storyboard(args.storyboard, args.content_root)
    if model is None:
        return _EXIT_INVALID_INPUT

    try:
        article = _article_for(args, required=True)
        media = load_media(args.media, args.storyboard) if args.media else None
        frame_range = _parse_frame_range(args.frame_range, media.storyboard.total_frames if media else model.total_frames) if args.frame_range else None
        if not 0 < args.scale <= 1:
            raise A2VError("--scale 只接受大于 0 且不超过 1 的比例")
        if args.purpose == "review" and (article is None or not Path(args.out or "").resolve().is_relative_to(article.preview_dir.resolve())):
            raise A2VError("审片输出必须写入作品 outputs/previews/ 目录")
        if args.purpose == "final" and args.scale != 1:
            raise A2VError("正式成片固定使用分镜原始尺寸；--scale 仅用于 --purpose review")
        if args.purpose == "final" and args.frame_range:
            raise A2VError("局部帧区间只允许用于评审输出；正式成片必须渲染完整时间轴")
        gate_error = None if args.purpose == "review" else _aesthetic_render_gate(args.storyboard, model, article, args.media)
        if gate_error:
            logging.error("渲染前审美门禁：%s", gate_error)
            return _EXIT_INVALID_INPUT
        # 契约页总是从查询参数读分镜（它就是为「一个页面服务任意作品」设计的）
        source_url = (
            _storyboard_url(args.storyboard, article) if article is not None else None
        )
        output = _resolve_render_output(args, model, media, article)
        # 这条路径不需要契约页：画面直接从 composition 的源码渲出来，
        # 契约页只在体检（量测与探针）时用来驱动同一份画面
        result = render_with_remotion(
                output=output,
                storyboard=model,
                storyboard_path=args.storyboard,
                crf=args.crf,
                preset=args.preset,
                limit_frames=args.limit_frames,
                timeout_ms=args.timeout,
                probe=not args.no_probe,
                media=media,
                storyboard_url=source_url,
                storyboard_origin=args.storyboard,
                workspace_root=article.workspace_root if article else None,
                content_root=args.content_root,
                frame_range=frame_range,
                scale=args.scale,
        )
    except (A2VError, OSError) as exc:
        logging.error("渲染失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("渲染被用户中断")
        return _EXIT_FAILED

    print(result.summary())
    return _EXIT_OK


def _aesthetic_render_gate(storyboard_path: str | Path, model: sb.Storyboard, article: paths_mod.ArticlePaths | None, media_path: str | Path | None = None) -> str | None:
    """所有 v3 分镜必须先有通过的审美体检。"""
    raw = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    if article is None:
        return "无法定位作品输出目录，请提供有效内容根"
    if isinstance(article, paths_mod.ArticlePaths):
        from . import production
        try:
            current = production.current_fingerprints(storyboard_path, media_path, article)
        except A2VError as exc:
            return str(exc)
        production_error = production.gate(production.record_path(article), json.loads(Path(storyboard_path).read_text(encoding="utf-8")), current)
        if production_error:
            return production_error
    report_path = article.output_dir / "inspect" / "report.json"
    review_path = article.output_dir / "inspect" / "review.md"
    if not report_path.is_file():
        return f"缺少 {report_path}，请先运行 review.py"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"无法读取 {report_path}: {exc}"
    aesthetic = report.get("aestheticReview") or {}
    failures = [item for item in aesthetic.get("findings") or [] if item.get("status") == "fail"]
    if failures:
        return "；".join(str(item.get("detail") or item.get("rule")) for item in failures)
    dynamic_review = report.get("bespokeAnimationReview") or {}
    if dynamic_review.get("required") and not dynamic_review.get("publishable"):
        return f"定制动画动态评审{dynamic_review.get('status', '待评审')}"
    if not review_path.is_file():
        return "缺少 review.md 人工审美结论"
    review = review_path.read_text(encoding="utf-8")
    if "- 是否值得发布：通过" not in review:
        return "review.md 尚未填写“是否值得发布：通过”"
    return None


def _parse_frame_range(text: str, total_frames: int) -> tuple[int, int]:
    import re
    match = re.fullmatch(r"(\d+)-(\d+)", text)
    if not match:
        raise A2VError(f"--frame-range 需要 start-end 格式，收到 {text!r}")
    start, end = map(int, match.groups())
    if start > end or end >= total_frames:
        raise A2VError(f"全局帧区间 {start}-{end} 超出分镜范围 0-{total_frames - 1}")
    return start, end


def _validated_storyboard(path: str | Path, content_root: str | Path | None = None) -> sb.Storyboard | None:
    """加载并校验分镜；有错误时打印问题并返回 None。

    代码场景的模块检查也在这里完成：预览、评审与渲染都会先走这一步，
    因此「模块不存在、没有默认导出」会在启动浏览器或打包之前失败，
    而不是渲出一张空画面再让人反推原因。
    """
    model, report = sb.load(path)
    _check_code_scene_modules(Path(path), content_root, report)
    if model is None:
        for issue in report.errors:
            logging.error("%s", issue.format())
        logging.error("分镜脚本校验未通过，已终止渲染")
        return None
    for issue in report.warnings:
        logging.warning("%s", issue.format())
    return model


def _check_code_scene_modules(
    path: Path, content_root: str | Path | None, report: Report
) -> None:
    """把代码场景的模块解析检查并入校验报告。

    模块存在性与导出契约需要作品归属（``scenes/`` 在文章目录下）；
    归属推不出来而分镜又声明了代码场景时，如实报错而不是静默跳过——
    静默跳过等于让缺失的模块在渲染期才暴露。
    """
    from . import code_scenes as cs

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return  # 分镜读不出来时 sb.load 已经报过；这里不重复报
    if not any(True for _ in cs.iter_code_scenes(data)):
        return
    try:
        article = paths_mod.for_storyboard(path, content_root)
    except A2VError as exc:
        for scene_path, _scene, _module in cs.iter_code_scenes(data):
            report.error(f"{scene_path}.renderer.module", f"无法推导作品归属，解析不了代码场景模块：{exc}")
        return
    for scene_path, message in cs.check(data, article.source_dir):
        report.error(scene_path, message)


def _v_gate_detail(gate: dict) -> str:
    """V 闸门的终端一行值：实际值与阈值并排，失败时列出场景。"""
    gate_id = gate.get("id")
    if gate_id == "V1":
        return f"文字幕 {gate.get('value')}/{gate.get('sceneCount')} 幕（上限 {gate.get('limit')}）"
    if gate_id == "V2":
        pairs = gate.get("pairs") or []
        return "相邻文字幕：" + "、".join(f"{a}→{b}" for a, b in pairs) if pairs else "无相邻文字幕"
    if gate_id == "V3":
        modes = "、".join(gate.get("modes") or []) or "无"
        return f"非文字模式 {gate.get('value')}/{gate.get('required')} 种（{modes}）"
    if gate_id == "V4":
        scenes = gate.get("scenes") or []
        if not scenes:
            return "声明与结构一致"
        return "矛盾：" + "、".join(f"{item.get('id')}({item.get('declaredMode')})" for item in scenes)
    return str(gate.get("status"))


def _v_gate_error_message(gate: dict) -> str:
    """V1–V4 失败进入错误列表时的完整描述：场景 id、实际值与阈值。"""
    gate_id = gate.get("id")
    if gate_id == "V1":
        return (
            f"文字幕 {gate.get('value')}/{gate.get('sceneCount')} 幕，超过允许上限 {gate.get('limit')}"
            f"（场景数 × {vn.TEXT_SCENE_RATIO:.0%} 向上取整）：涉及 {'、'.join(gate.get('scenes') or [])}"
        )
    if gate_id == "V2":
        pairs = "、".join(f"{a}→{b}" for a, b in gate.get("pairs") or [])
        return f"相邻两幕均为文字幕：{pairs}"
    if gate_id == "V3":
        modes = "、".join(gate.get("modes") or []) or "无"
        return (
            f"非文字视觉模式只有 {gate.get('value')} 种（{modes}），"
            f"少于 {gate.get('sceneCount', '')} 幕规模要求的 {gate.get('required')} 种"
        )
    scenes = gate.get("scenes") or []
    return "声明与结构矛盾：" + "；".join(
        f"{item.get('id')} 声明为 {item.get('declaredMode')} 但只有文字与包装节点（证据：{'、'.join(item.get('evidence') or []) or '无'}）"
        for item in scenes
    )


def _animation_review_payload(
    storyboard_path: Path, media: Any, out_dir: Path, combined: Report
) -> dict:
    """动画论证 A 系列：A1–A5、A7、A8 硬判定并入错误数，A6 由人工裁决。

    与 V 系列同一口径：机检结论进错误数与退出码，人工结论只呈现。
    有媒体时用清单里的派生时长与字幕边界，无声时按声明时长等比例估算，
    并把 A4 如实写成「跳过」而不是通过。
    """
    from . import animation_review as ar

    raw = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    analysis = ar.analyze(raw, media.data if media is not None else None)
    gates = ar.review_gates(analysis)
    for where, message in ar.gate_issues(gates):
        combined.error(where, message)
    gates["a6"] = ar.review_a6(out_dir / "review.md", analysis)
    return gates


def _bespoke_animation_review_payload(storyboard_path: Path, out_dir: Path) -> dict:
    from . import bespoke_review

    raw = json.loads(storyboard_path.read_text(encoding="utf-8"))
    return bespoke_review.review(out_dir / "review.md", raw)


def _animation_review_lines(result: dict | None) -> list[str]:
    """A 系列的终端摘要：机检逐条给结论，人工结论单列一行。"""
    if not result:
        return []
    from . import animation_review as ar

    lines = ["动画论证 A 系列（A1–A5/A7/A8 机检并进错误数；A6 人工裁决）："]
    for gate_id in ar.MACHINE_GATES:
        gate = result.get(gate_id.lower()) or {}
        status = str(gate.get("status"))
        mark = {"pass": "✓", "fail": "✗"}.get(status, "-")
        lines.append(f"  {mark} {gate_id} {gate.get('title')}：{gate.get('detail')}")
    a6 = result.get("a6") or {}
    score = a6.get("score")
    score_text = f"{score}/5" if isinstance(score, int) else "未填写"
    lines.append(
        f"  - A6 装饰动画人工裁决：{a6.get('status')}（{score_text}）"
        f"——可发布={'是' if a6.get('publishable') else '否'}"
    )
    return lines


def _visual_narrative_payload(storyboard_path: Path, out_dir: Path, combined: Report) -> dict:
    """视觉叙事 V 系列：V1–V4 硬判定并入错误数，V5 证据与 V6 人工结论只呈现。

    V1–V4 与严格校验同一口径（同一份 visual_narrative 分析）；V5 是
    文字主导候选清单，V6 从 ``review.md`` 读人工结论，缺失即「待评审」，
    低于 4/5 或存在未裁决候选时不可发布。语义结论不并入自动退出码。
    """
    raw = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    gates = vn.review_gates(vn.analyze(raw))
    for gate in (gates["v1"], gates["v2"], gates["v3"], gates["v4"]):
        if gate["status"] == "fail":
            combined.error(f"视觉叙事 {gate['id']}", _v_gate_error_message(gate))
    candidates = [item["id"] for item in gates["v5"]["scenes"]]
    gates["v6"] = vn.review_v6(out_dir / "review.md", candidates)
    return gates


def _visual_narrative_lines(vn_result: dict | None) -> list[str]:
    """V 系列的终端摘要。分开呈现机检结论与人工结论，不合成总分。"""
    if not vn_result:
        return []
    lines = ["视觉叙事 V 系列（V1–V4 与严格校验同口径；V5/V6 语义结论只提示）："]
    for key in ("v1", "v2", "v3", "v4"):
        gate = vn_result.get(key) or {}
        mark = "✓" if gate.get("status") == "pass" else "✗"
        lines.append(f"  {mark} {gate.get('id')} {gate.get('title')}：{_v_gate_detail(gate)}")
    v5 = vn_result.get("v5") or {}
    ids = [str(item.get("id")) for item in v5.get("scenes") or []]
    lines.append(f"  - V5 文字主导候选：{'、'.join(ids) if ids else '无'}（判定证据见 report.json，需逐条裁决）")
    v6 = vn_result.get("v6") or {}
    score = v6.get("score")
    score_text = f"{score}/5" if isinstance(score, int) else "未填写"
    lines.append(
        f"  - V6 图形承担论证：{v6.get('status')}（{score_text}）——可发布={'是' if v6.get('publishable') else '否'}"
    )
    return lines


def _article_for(
    args: argparse.Namespace, *, required: bool = False
) -> paths_mod.ArticlePaths | None:
    """本次调用涉及的文章归属。

    推不出来时默认返回 None，而不是在这里抛错：显式给出 `--out` 的调用方式
    本来就不需要归属，报错应当留给真正需要归属的那一步（默认输出路径、
    媒体归属）。Remotion 路径例外（`required=True`）：分镜 URL 与默认输出
    都按工作区根拼，没有归属就没有可用的输入。
    """
    try:
        return paths_mod.for_storyboard(args.storyboard, args.content_root)
    except A2VError as exc:
        if required:
            raise
        logging.debug("未能推导文章归属：%s", exc)
        return None


def _storyboard_url(storyboard: str | Path, article: paths_mod.ArticlePaths) -> str:
    """契约页加载分镜的 URL 路径：相对**工作区根**，与服务静态根一致。"""
    return contract_page.storyboard_url(storyboard, article.workspace_root)


def _with_storyboard_query(
    url: str, storyboard: str | Path, article: paths_mod.ArticlePaths
) -> str:
    """给契约页 URL 补上 `a2v-storyboard` 查询参数。

    契约页从该参数指定的路径加载分镜，服务在起服务前就拼好了它；体检走的是
    通用的「本地页面 → URL」转换，因此在这里补上，否则页面会因缺少参数
    直接报错，探针拿不到任何场景。
    """
    from urllib.parse import quote

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}a2v-storyboard={quote(_storyboard_url(storyboard, article), safe='')}"


def _with_query_param(url: str, name: str, value: str) -> str:
    """给 URL 补上一个取值为绝对地址（或任意字符串）的查询参数。"""
    from urllib.parse import quote

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{name}={quote(value, safe='')}"


def _resolve_render_output(
    args: argparse.Namespace,
    model: sb.Storyboard | None,
    media: Media | None,
    article: paths_mod.ArticlePaths | None = None,
) -> Path:
    """确定成片路径：显式 --out 优先，否则按文章归属推导。

    推导需要分镜：它决定成品是 silent 还是 voiced。因此省略 --out 且缺少
    --storyboard 时明确报错，而不是猜测文件名。
    """
    if args.out:
        return Path(args.out)
    if article is None:
        try:
            article = paths_mod.for_storyboard(args.storyboard, args.content_root)
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
        media_article = paths_mod.for_storyboard(args.storyboard, args.content_root)
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

    model, report = sb.load(path, strict=args.strict)
    _check_code_scene_modules(path, args.content_root, report)
    diversity_result = None
    if model is not None:
        try:
            from . import diversity
            raw = json.loads(path.read_text(encoding="utf-8"))
            refs = diversity.load_references(args.reference) if args.reference else None
            diversity_result = diversity.inspect(raw, refs)
            for finding in diversity_result["findings"]:
                report.warn("scenes", f"多样性规则 {finding['rule']}：涉及场景 {', '.join(finding['scenes'])}")
        except (OSError, json.JSONDecodeError) as exc:
            report.error("reference", f"参考分镜读取失败：{exc}")
            model = None
    if args.media and model is not None:
        try:
            model = load_media(args.media, path).storyboard
        except (A2VError, OSError) as exc:
            report.error("media", str(exc))
            model = None
    if args.json:
        payload = report.to_json()
        if diversity_result is not None:
            payload["diversity"] = diversity_result
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

    from .media import media_url, write_effective_storyboard
    if not args.storyboard or _validated_storyboard(args.storyboard, args.content_root) is None:
        logging.error("Remotion 预览需要有效的 --storyboard")
        return _EXIT_INVALID_INPUT
    try:
        article = paths_mod.for_storyboard(args.storyboard, args.content_root)
        _build_contract_for(args.storyboard, article.repo_root, args.content_root)
        page = contract_page.require_contract_page(article.repo_root)
        page_mounts = contract_page.web_mounts(article.repo_root)
        source_url = _storyboard_url(args.storyboard, article)
        serve_root = article.workspace_root
    except A2VError as exc:
        logging.error("预览失败: %s", exc)
        return _EXIT_INVALID_INPUT

    media_server = None
    try:
        media = load_media(args.media, args.storyboard or page.parent / "storyboard.json") if args.media else None
        if media:
            media_server = LocalServer(media.path.parent, cors=True)
    except (A2VError, OSError) as exc:
        logging.error("预览失败: %s", exc)
        return _EXIT_INVALID_INPUT
    # 契约页在仓库的 web/ 下、分镜在工作区根下：靠别名挂载把两棵树接起来
    server = LocalServer(serve_root, port=args.port, mounts=page_mounts)
    try:
        from urllib.parse import urlencode
        server.start()
        url = server.url_for(page)
        if media is not None and media_server is not None:
            # 画面时间轴必须与音轨一致：契约页的 props 用媒体派生的有效分镜
            # （写入媒体目录、由媒体服务提供），而不是声明时长的原始分镜
            media_base = media_server.start()
            effective = write_effective_storyboard(media)
            url += "?" + urlencode({"a2v-storyboard": f"{media_base}/{effective.name}"})
            url = media_url(url, media_base, media)
        elif source_url:
            url += "?" + urlencode({"a2v-storyboard": source_url})
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


def _build_contract_for(
    storyboard: str | Path, repo_root: Path, content_root: str | Path | None = None
) -> None:
    """为当前作品生成入口与代码场景清单并构建契约页，保证预览/体检与导出使用同一模块。"""
    from . import remotion as remotion_mod

    web = contract_page.web_dir(repo_root)
    remotion_mod.prepare_composition_entry(
        web_dir=web, storyboard_path=storyboard, content_root=content_root
    )
    remotion_mod._run(
        [remotion_mod.program("pnpm"), "build"],
        cwd=web,
        timeout_s=600,
        what="构建 Remotion 契约页",
    )


def main_review(argv: list[str] | None = None) -> int:
    """视觉评审：一次跑完帧量测、契约探针与观感闸门。"""
    args = _build_review_parser().parse_args(argv)
    _force_utf8_output()
    _configure_logging(args.verbose)

    from . import inspect as inspect_mod
    from . import aesthetic_review
    from . import storyboard as sb
    from .browser import open_animated_page
    from .media import load_media, media_url, write_effective_storyboard
    from .render import _resolve_page_url

    article: paths_mod.ArticlePaths | None = None
    page_mounts: dict[str, Path] | None = None
    try:
        article = paths_mod.for_storyboard(args.storyboard, args.content_root)
        _build_contract_for(args.storyboard, article.repo_root, args.content_root)
        page_file = contract_page.require_contract_page(article.repo_root)
        page_mounts = contract_page.web_mounts(article.repo_root)
    except A2VError as exc:
        logging.error("找不到要体检的画面: %s", exc)
        return _EXIT_INVALID_INPUT

    model, report = sb.load(args.storyboard)
    if model is None or not report.ok:
        for issue in report.issues:
            logging.error("%s", issue.format())
        logging.error("分镜脚本校验未通过，无法体检")
        return _EXIT_INVALID_INPUT
    # 代码场景模块在起浏览器之前检查：缺失模块或错误导出在这里就失败
    code_report = Report()
    _check_code_scene_modules(Path(args.storyboard), args.content_root, code_report)
    if not code_report.ok:
        for issue in code_report.errors:
            logging.error("%s", issue.format())
        logging.error("代码场景模块校验未通过，无法体检")
        return _EXIT_INVALID_INPUT

    try:
        media = load_media(args.media, args.storyboard) if args.media else None
        scenes = inspect_mod.scenes_as_dicts(media.storyboard if media else model)
    except (A2VError, OSError) as exc:
        logging.error("体检失败: %s", exc)
        return _EXIT_FAILED

    out_dir = Path(args.out_dir) if args.out_dir else _default_review_dir(args, article)
    _ensure_aesthetic_review_template(out_dir, [str(scene.get("id", "")) for scene in scenes])
    # 静态确定性由 `source_policy.py` 对 composition 可达源码的扫描负责（打包时执行）。
    # 这里**明说跳过**而不是安静照过：按契约页的 HTML 查结构只会报出一堆假问题
    # （画面由 composition 源码决定，契约页 HTML 里只有一个挂载点与一个入口脚本），
    # 而一声不吭的检查与通过的检查在报告里长得一样。
    combined = Report()
    combined.warn(
        "静态确定性",
        "由 source_policy.py 在打包 composition 时对可达源码扫描；"
        "本步骤运行 DOM 量测与契约探针",
    )
    # 视觉叙事 V 系列是静态分析，放在浏览器工作之前：契约页构建失败时
    # 它的结论也已经被写进错误列表，不会因为环境问题静默丢失。
    visual_narrative = _visual_narrative_payload(Path(args.storyboard), out_dir, combined)
    # 动画论证 A 系列同理：它读分镜与媒体清单，不需要浏览器。机检失败在这里
    # 就进错误数，契约页起不来也不影响「动画有没有解释论点」的结论。
    animation_review = _animation_review_payload(Path(args.storyboard), media, out_dir, combined)
    raw_storyboard = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    bespoke_animation_review = _bespoke_animation_review_payload(Path(args.storyboard), out_dir)
    aesthetic_review_result = aesthetic_review.analyze(raw_storyboard)
    for finding in aesthetic_review_result["findings"]:
        if finding["status"] == "fail":
            combined.error(f"导演预检 {finding['rule']}", finding["detail"] + "：" + "、".join(finding["scenes"]))

    try:
        with contextlib.ExitStack() as stack:
            # 页面与分镜常常不在同一棵树里：静态根取文章的工作区根（分镜与作品
            # 资产在这里），页面本身由别名提供——契约页在仓库的 web/ 下，
            # 旧共享页面在 skill 资产下。
            serve_root = article.workspace_root if article is not None else None
            url = stack.enter_context(_resolve_page_url(page_file, serve_root, page_mounts))
            if media:
                # 画面时间轴必须与音轨一致：契约页的 props 用媒体派生的有效
                # 分镜（写入媒体目录、由带 CORS 的媒体服务提供），而不是
                # 声明时长的原始分镜——否则体检按派生时长抽帧，页面却按
                # 声明时长解释帧号，采样帧会落进下一幕入场前的空窗。
                media_server = stack.enter_context(LocalServer(media.path.parent, cors=True))
                effective = write_effective_storyboard(media)
                url = _with_query_param(
                    url, "a2v-storyboard", f"{media_server.base_url}/{effective.name}"
                )
                url = media_url(url, media_server.base_url, media)
            elif article is not None:
                url = _with_storyboard_query(url, args.storyboard, article)
            with open_animated_page(
                url,
                timeout_ms=args.timeout,
                width=model.width,
                height=model.height,
                expected_version=contract_page.CONTRACT_VERSION,
            ) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                preset = str(((media.storyboard if media else model).visual or {}).get("preset") or "")
                page_report, extra = inspect_mod.run_inspect(
                    page, scenes, out_dir / "frames", out_dir, preset=preset,
                    sheet_name=_contact_sheet_name("media" if media else "storyboard"),
                )
                # 运行期隔离（任务 3.3）：被阻断请求、页面异常、未处理 Promise
                # 与控制台 error 都计为错误，而不是静默放行。
                runtime_violations = page.drain_violations()
                # 确定性验收（任务 6.4）：显式开启时对采样帧做重复求值判定
                determinism_verdicts = (
                    _determinism_acceptance(page, scenes) if args.check_determinism else None
                )
    except (A2VError, OSError, ValueError) as exc:
        logging.error("体检失败: %s", exc)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        logging.error("体检被用户中断")
        return _EXIT_FAILED

    for issue in page_report.issues:
        combined.add(issue.level, issue.path, issue.message)
    for violation in runtime_violations:
        combined.error("运行期隔离", violation)
    determinism_json = _apply_determinism_verdicts(combined, determinism_verdicts)
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
            "visualNarrative": visual_narrative,
            "animationReview": animation_review,
            "bespokeAnimationReview": bespoke_animation_review,
            "aestheticReview": aesthetic_review_result,
            **({"determinism": determinism_json} if determinism_json is not None else {}),
        },
        out_dir / "report.json",
    )

    for issue in combined.issues:
        print(issue.format(), file=sys.stderr)
    print(_review_summary(payload, out_dir))
    return _EXIT_OK if combined.ok else _EXIT_INVALID_INPUT


def _ensure_aesthetic_review_template(out_dir: Path, scene_ids: list[str] | None = None) -> None:
    """首次体检生成审美评审模板，已有人工结论绝不覆盖。"""
    target = out_dir / "review.md"
    if target.exists():
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(
        """# 视觉评审

> 本文件由 review.py 首次运行生成。请保留机检结果，并补齐人工裁决；再次运行不会覆盖本文件。

## 审美检查

| 维度 | 评分（1-5） | 依据 |
|---|---:|---|
| 核心论点清晰 |  |  |
| 图形论证 |  |  |
| 主次层级 |  |  |
| 跨幕变化 |  |  |
| 动效服务 |  |  |
| 视觉记忆点 |  |  |
| 结尾余韵 |  |  |

## 候选裁决

<!-- 按 report.json 中的 V5 候选逐条填写：- scene-id：通过 / 必改，理由…… -->

## A6 候选裁决

<!-- 按 report.json 中的 A6 候选逐条填写：- recipe / scene-id：通过 / 删除，理由…… -->

## 发布结论

- 是否值得发布：待评审
        """ + _dynamic_review_template(scene_ids or []),
        encoding="utf-8",
    )


def _dynamic_review_template(scene_ids: list[str]) -> str:
    rows = "\n".join(f"| {scene_id} |  |  |  |  |  |  |" for scene_id in scene_ids)
    return (
        "\n\n## 定制动画动态评审\n\n"
        "<!-- 使用代码场景时填写状态与每幕五项评分；依据须来自播放，标明时间或帧。 -->\n"
        "状态：待评审\n\n"
        "| 场景 | 焦点清晰度 | 动作解释力 | 节奏变化 | 转场连贯性 | 结果可读性 | 依据 |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |\n"
        f"{rows}\n"
    )


def _determinism_acceptance(page: Any, scenes: list[dict]) -> list:
    """同帧重复截图 + 随机寻帧的确定性验收（任务 6.4）。

    每幕取收尾帧；`produce` 先跳到别的帧再回来——逼出「残留状态」类的
    非确定性（图表实例的脏状态、累积的随机序列），同帧连拍两下抓不到它。
    判据沿用现有相似度门槛（PSNR ≥ 60 dB）。
    """
    from . import determinism as determinism_mod
    from . import inspect as inspect_mod

    total = sum(int(scene.get("durationInFrames") or 0) for scene in scenes) or 1
    frames = [window[-1] for _s, _start, _end in inspect_mod.scene_windows(scenes) for window in [inspect_mod.sample_frames(_start, _end)]]

    def produce(frame: int) -> bytes:
        page.evaluate(
            "({frame, total}) => window.__A2V__.seekToFrame((frame + 13) % total)",
            {"frame": frame, "total": total},
        )
        page.seek(frame)
        return page.capture("png")

    return determinism_mod.judge_frames(produce, frames, threshold=determinism_mod.DEFAULT_PSNR_DB)


def _apply_determinism_verdicts(combined: Report, verdicts: list | None) -> list[str] | None:
    """把确定性验收结论并入评审报告；失败是错误，影响退出码。

    返回给 report.json 的描述列表（未开启验收时为 None，不写字段）。
    """
    if verdicts is None:
        return None
    for verdict in verdicts:
        if not verdict.ok:
            combined.error("确定性", verdict.describe())
    return [verdict.describe() for verdict in verdicts]


def _default_review_dir(args, article: paths_mod.ArticlePaths | None) -> Path:
    """体检产物目录：作品目录下的 `outputs/inspect`，与渲染产物放在一起。

    专属网页优先按网页归属；共享页面不在 `videos/`、`examples/` 下，
    此时回退到分镜归属，与渲染入口的推导保持一致。两者都推不出来时
    由调用方显式给出的 `--out-dir` 兜底（本函数只在未给出时被调用）。
    """
    if article is None:
        article = paths_mod.for_storyboard(args.storyboard, args.content_root)
    target = article.output_dir / "inspect"
    logging.info("未指定 --out-dir，体检产物写入 %s", target)
    return target


def _font_findings(page_file: Path, args) -> list[dict]:
    """按画面实际注册的字体查缺字（`narration` 等不渲染的字段不进扫描）。

    「画面实际注册的字体」在两个引擎里是不同的东西：旧页面写在样式表的
    `@font-face` 里，React 路径由 `src/fonts.ts` 在运行时注册、清单落在
    `src/assets/fonts.json`。因此字体文件从哪里取是引擎相关的一步，
    判定本身共用 `fonts.audit_fonts`。
    """
    path = Path(args.storyboard) if args.storyboard else None
    if path is None or not path.is_file():
        return []
    try:
        storyboard = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    try:
        repo_root = paths_mod.for_storyboard(args.storyboard, args.content_root).repo_root
        registered = contract_page.font_files(repo_root)
        if not registered:
            return [{"where": "字体覆盖", "skip": "字体清单为空，字体覆盖检查不适用"}]
        return fonts_mod.audit_fonts(registered, storyboard)
    except (A2VError, OSError, ValueError) as exc:
        logging.warning("字体覆盖检查跳过：%s", exc)
        return []


def _rendered_provenance(out_dir: Path) -> dict:
    """这个作品的成片是不是旧资产渲的。

    成片与体检产物同属一个作品目录（`videos/<slug>/outputs/voiced.mp4` 对
    `videos/<slug>/outputs/inspect/`），所以从体检目录往上一级找成片。
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


def _contact_sheet_name(source: Any) -> str:
    """联系表文件名由抽帧时间轴决定。

    静态材料 `contact-sheet.png` 只按**分镜声明的时间轴**生成（视觉评审量表：
    静态联系表不读媒体）。带 `--media` 的体检按配音派生的时长抽帧，画的其实是
    另一批帧，必须写到另一个文件名，否则会覆盖 production.json 已登记的静态
    材料，让门禁报「材料已缺失或摘要已变化」——而画面一个字都没变。
    """
    return "contact-sheet-media.png" if source == "media" else "contact-sheet.png"


def _review_summary(payload: dict, out_dir: Path) -> str:
    """终端摘要与 AI 助手后续视觉评审指引。"""
    lines = [
        f"体检完成：{payload['frameCount']} 帧抽检，"
        f"{payload['summary']['errors']} 个错误，{payload['summary']['warnings']} 个提醒",
        f"产物：{out_dir / 'report.json'}",
        f"联系表：{out_dir / _contact_sheet_name(payload.get('source'))}",
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

    lines.extend(_visual_narrative_lines(payload.get("visualNarrative")))

    lines.extend(_animation_review_lines(payload.get("animationReview")))

    dynamic = payload.get("bespokeAnimationReview") or {}
    if dynamic.get("required"):
        lines.append(f"定制动画动态评审：{dynamic.get('status')}；可发布={'是' if dynamic.get('publishable') else '否'}")

    lines.extend(_provenance_lines(payload.get("provenance")))

    lines.append("接下来由 article2video AI 助手按 references/visual-review-rubric.md 查看画面并填写制作记录。")
    return "\n".join(lines)


#: 观感闸门里的硬判定。它们与「不是废片」类检查同性质：不通过就不该出片。
#: 其余观感闸门只提示——「不够发布会级」和「画面坏了」不是一回事。
#:
#: K7 是「文字越出安全区」，K8 是「图形内文字穿出自己的容器」。两者都是
#: 有人会看到半行字的画面损坏；K8 的存在还因为 K7 的参照只有安全区，
#: 图形内部按几何位置绘制的文字完全不在它的量程内。
_HARD_GATES = ("K7", "K8")


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
        return [f"观感闸门 K1–K10：不适用——{keynote.get('reason') or '未启用设计语言预设'}"]
    summary = keynote.get("summary") or {}
    lines = [
        "观感闸门 K1–K10（与上面的废片类检查分开计）："
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
        "--content-root",
        help="文章与产物所在的工作区根；省略时读环境变量 A2V_CONTENT_ROOT，"
        "两者都没有则用仓库根",
    )
    parser.add_argument(
        "--out-dir",
        help="媒体输出目录；省略时按文章归属推导为 videos/<slug>/outputs/media",
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
        article = paths_mod.for_storyboard(args.storyboard, args.content_root)
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
    """配音准备的默认输出目录：作品目录下的 `outputs/media`。"""
    logging.info("未指定 --out-dir，写入 %s", article.media_dir)
    return article.media_dir


def _reject_foreign_media_dir(article: paths_mod.ArticlePaths, out_dir: str | Path) -> None:
    """拒绝把媒体写进另一篇文章的作品目录。

    项目外的临时目录（测试、调试）仍然允许；只有明确落在工作区作品目录的
    `outputs/media` 时才判为冲突，避免清单和音轨被写进别人的产物目录。
    """
    resolved = Path(out_dir).resolve()
    if resolved == article.media_dir:
        return
    if resolved == article.media_dir:
        return
    if resolved.name != paths_mod.MEDIA_DIR:
        return
    try:
        workspace_relative = resolved.relative_to(article.workspace_root.resolve())
    except ValueError:
        return
    if "outputs" in workspace_relative.parts and resolved.parent != article.output_dir.resolve():
        raise A2VError(
            f"--out-dir {resolved} 属于其他文章的媒体目录，本篇文章应使用 {article.media_dir}"
        )
