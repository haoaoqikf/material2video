"""``m2v ref`` 的薄命令层：解析已由 ``m2v.cli`` 完成，这里只执行并打印。"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.reference.audio import extract_audio
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


def _audio(args) -> int:
    if not args.project:
        raise M2VError("ref audio 需要 --project <作品目录>")
    if not args.user_authorized:
        raise M2VError('复用参考音轨必须提供 --user-authorized "<用户授权说明>"')
    if args.output or args.headed:
        raise M2VError("ref audio 不接受 --output 或 --headed")
    result = extract_audio(args.target, args.project, statement=args.user_authorized,
                           name=args.name, force=args.force)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    info, timeline = result["audioInfo"], result["timeline"]
    state = "已存在且摘要一致，复用" if result["reused"] else "已提取"
    print(f"{state}：{result['audio']}")
    print(f"  时长 {info['durationSeconds']:.3f} 秒；{info['sampleRate']} Hz；"
          f"{info['channels']} 声道；{info['bitsPerSample']}-bit")
    print(f"  60 fps 总帧数：{timeline['totalFrames']}"
          f"（向上取整，尾部最多补 {timeline['tailSilenceMaxMs']} ms 静音）")
    print(f"来源：抖音 @{result['source']['author']}；作品 {result['source']['awemeId']}")
    print(f"授权：{result['authorization']['statement']}")
    print(f"许可：{result['authorization']['licenseStatus']}")
    print(f"片尾保留：音频：抖音 @{result['source']['author']}（用户指定复用）｜画面原创")
    print("可直接粘贴：")
    print(json.dumps({"soundtrack": result["soundtrack"]}, ensure_ascii=False, indent=2))
    print(f"全部 cut：sum(durationFrames) = {timeline['totalFrames']}；"
          f"使用 fade/crossfade：另加 transitionFrames 之和。")
    if result.get("warning"):
        print(f"注意：{result['warning']}")
    print("音轨摘要已进入准备输入；如准备记录早于本次提取，请重新 prepare。")
    return 0


def main(args) -> int:
    if args.workflow == "audio":
        return _audio(args)
    if args.project or args.name or args.user_authorized:
        raise M2VError("--project / --name / --user-authorized 只用于 ref audio")

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
