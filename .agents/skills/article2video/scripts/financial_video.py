#!/usr/bin/env python
"""Initialize, validate, and render a no-audio financial time-series video."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v import financial, financial_render  # noqa: E402
from a2v.cli import _force_utf8_output  # noqa: E402
from a2v.errors import A2VError  # noqa: E402


def _project_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _add_init(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-dir", required=True, help="作品目录，如 videos/acme-2010-2024")
    parser.add_argument("--kind", required=True, choices=("stock", "index"))
    parser.add_argument("--name", required=True, help="公司或指数名称")
    parser.add_argument("--code", required=True, help="证券/指数代码")
    parser.add_argument("--market", required=True, help="市场标识，例如 NASDAQ、HKEX、SSE")
    parser.add_argument("--unit", required=True, help="股票币种或指数点位单位")
    parser.add_argument("--start-date", required=True, help="展示开始日 YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="展示结束日 YYYY-MM-DD")
    parser.add_argument("--listing-date", help="股票上市日期 YYYY-MM-DD")
    parser.add_argument("--index-start-date", help="指数发布起始日期 YYYY-MM-DD")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="financial_video.py", description="金融时间序列视频的离线材料准备、校验和渲染")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="生成待 AI 搜索资料并填充的作品材料模板")
    _add_init(init)
    validate = sub.add_parser("validate", help="离线校验四类作品材料与帧时间轴")
    validate.add_argument("--project-dir", required=True)
    render = sub.add_parser("render", help="离线渲染并验收无音轨横屏 MP4")
    render.add_argument("--project-dir", required=True)
    render.add_argument("--out", help="输出 MP4；默认 <project-dir>/outputs/financial-timeseries.mp4")
    render.add_argument("--limit-frames", type=int, help="快速预演前 N 帧，写入 outputs/previews/")
    render.add_argument("--crf", type=int, default=18)
    render.add_argument("--preset", choices=("ultrafast", "veryfast", "fast", "medium", "slow", "slower"), default="medium")
    return parser


def _init(args: argparse.Namespace) -> Path:
    root = _project_path(args.out_dir)
    if root.exists() and any(root.iterdir()):
        raise A2VError(f"作品目录不是空目录：{root}")
    start, end = date.fromisoformat(args.start_date), date.fromisoformat(args.end_date)
    if start.isoformat() != args.start_date or end.isoformat() != args.end_date:
        raise A2VError("日期必须使用 YYYY-MM-DD 格式")
    if start > end:
        raise A2VError("开始日期不能晚于结束日期")
    if args.kind == "stock":
        if args.index_start_date:
            raise A2VError("股票不使用 --index-start-date")
        if not args.listing_date:
            raise A2VError("股票标的必须提供 --listing-date")
        listing = date.fromisoformat(args.listing_date)
        if listing.isoformat() != args.listing_date:
            raise A2VError("上市日期必须使用 YYYY-MM-DD 格式")
        if listing > start:
            raise A2VError("起始日早于上市日；请先确认实际展示范围")
    else:
        if args.listing_date:
            raise A2VError("指数不使用 --listing-date")
        if not args.index_start_date:
            raise A2VError("指数必须提供 --index-start-date")
        index_start = date.fromisoformat(args.index_start_date)
        if index_start.isoformat() != args.index_start_date:
            raise A2VError("指数起始日期必须使用 YYYY-MM-DD 格式")
        if start < index_start:
            raise A2VError("起始日早于指数发布日；请先确认实际展示范围")
    root.mkdir(parents=True, exist_ok=True)
    request = {
        "schemaVersion": 1,
        "originalRequest": f"{args.name} {start.year}年到{end.year}年股价/点位演变视频",
        "instrument": {
            "kind": args.kind, "name": args.name.strip(), "code": args.code.strip(),
            "market": args.market.strip(), "unit": args.unit.strip(),
            **({"listingDate": args.listing_date} if args.listing_date else {}),
            **({"indexStartDate": args.index_start_date} if args.index_start_date else {}),
        },
        "requestedRange": [start.isoformat(), end.isoformat()],
        "displayRange": [start.isoformat(), end.isoformat()],
        "confirmations": [],
    }
    _write(root / "request.json", request)
    _write(root / "prices.json", {
        "schemaVersion": 1, "unit": args.unit.strip(),
        "priceBasis": "split-adjusted" if args.kind == "stock" else "official-index-points",
        "adjustmentBaseDate": end.isoformat() if args.kind == "stock" else None,
        "adjustmentDefinition": "仅拆合股调整，不计分红再投资；由 AI 核验来源定义后填写" if args.kind == "stock" else None,
        "splitAdjustments": [], "indexType": "由 AI 核验发布机构定义后填写" if args.kind == "index" else None,
        "expectedTradingDates": [], "expectedTradingDatesSource": [], "points": [], "sources": [], "rawSnapshots": [],
    })
    _write(root / "events.json", {"schemaVersion": 1, "candidates": [], "selected": [], "excluded": []})
    _write(root / "animation-plan.json", {
        "schemaVersion": 1, "durationSeconds": None, "fps": 30, "canvas": {"width": 1920, "height": 1080},
        "axis": {"dateRange": [start.isoformat(), end.isoformat()], "valueRange": [0, 1]},
        "segments": [], "eventDisplays": [], "rationale": "由 AI 根据数据跨度和入选事件编排并填写",
    })
    return root


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _force_utf8_output()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    try:
        if args.command == "init":
            root = _init(args)
            print(f"已初始化金融时间序列作品材料：{root}")
            print("请由 AI 搜索并核验数据与事件，填写四份材料后运行 validate。")
            return 0
        root = _project_path(args.project_dir)
        docs = financial.load_project(root)
        if args.command == "validate":
            print(f"金融视频材料校验通过：{root}")
            print(f"交易日 {len(docs['prices']['points'])} 个，入选事件 {len(docs['events']['selected'])} 个，时长 {docs['plan']['durationSeconds']} 秒")
            return 0
        output = Path(args.out).expanduser().resolve() if args.out else None
        result = financial_render.render(
            root, docs, output=output, limit_frames=args.limit_frames,
            crf=args.crf, preset=args.preset,
        )
        print(f"金融视频已渲染并通过无音轨验收：{result}")
        return 0
    except (A2VError, ValueError, OSError) as exc:
        print(f"金融视频制作失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
