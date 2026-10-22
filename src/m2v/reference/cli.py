"""``m2v ref`` 的薄命令层：解析已由 ``m2v.cli`` 完成，这里只执行并打印。"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.reference.douyin import fetch, verify_directory


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _summary(result) -> dict:
    item = result.item
    return {
        "directory": str(result.directory),
        "awemeId": item["awemeId"],
        "kind": item["kind"],
        "reused": result.reused,
        "author": item["author"]["nickname"],
        "desc": item["desc"],
        "durationMs": item["durationMs"],
        "files": result.files,
    }


def main(args) -> int:
    if args.workflow == "fetch":
        result = fetch(
            args.target,
            output=args.output,
            headed=args.headed,
            force=args.force,
        )
        if args.json:
            print(json.dumps(_summary(result), ensure_ascii=False, indent=2))
            return 0
        print(f"{'已存在，校验通过' if result.reused else '已保存'}：{result.directory}")
        kind = "图文" if result.item["kind"] == "note" else "视频"
        duration = result.item["durationMs"] / 1000
        duration_text = f"，{duration:.1f} 秒" if duration else ""
        print(f"类型：{kind}{duration_text}；作者：{result.item['author']['nickname'] or '未知'}")
        if result.item["desc"]:
            print(f"文案：{result.item['desc'].splitlines()[0][:60]}")
        for record in result.files:
            measured = ""
            if record.get("width") and record.get("height"):
                measured = f" {record['width']}×{record['height']}"
            print(f"  {record['path']}（{_human_bytes(record['bytes'])}{measured}）")
        return 0

    directory = Path(args.target)
    files = verify_directory(directory)
    if args.json:
        print(json.dumps({"directory": str(directory.resolve()), "files": files},
                         ensure_ascii=False, indent=2))
    else:
        print(f"校验通过：{directory.resolve()}（{len(files)} 个文件）")
    return 0
