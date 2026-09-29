#!/usr/bin/env python
"""查询作品制作流程并展示可复制的 production.json 模板。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v import paths, production  # noqa: E402
from a2v.cli import _force_utf8_output  # noqa: E402
from a2v.errors import A2VError  # noqa: E402
from a2v.storyboard import load as load_storyboard  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="production.py", description="查询制作阶段或输出 production.json 模板")
    parser.add_argument("command", choices=("status", "template", "keyframes", "samples", "rehearsal"))
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--media")
    parser.add_argument("--content-root")
    parser.add_argument("--out", help="template 命令的 UTF-8 production.json 写入路径")
    args = parser.parse_args(argv)
    _force_utf8_output()
    try:
        article = paths.for_storyboard(args.storyboard, args.content_root)
        raw = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
        if args.media is None and args.command != "keyframes" and article.media_manifest.is_file():
            args.media = str(article.media_manifest)
        model, report = load_storyboard(args.storyboard)
        if model is None:
            raise A2VError("分镜校验失败：" + "；".join(item.format() for item in report.errors))
        record_file = production.record_path(article)
        stale_media = False
        try:
            current = production.current_fingerprints(args.storyboard, args.media, article)
        except A2VError as exc:
            # A status query must explain stale narration inputs instead of
            # failing before it can show the next actionable preparation step.
            if args.command != "status" or "请重新 prepare" not in str(exc):
                raise
            stale_media = True
            current = production.current_fingerprints(args.storyboard, None, article)
            current["media"] = "stale"
        if args.command == "template":
            record = production.initialize_template(raw, current)
            record["materialRoot"] = os.path.relpath(article.workspace_root.resolve(), record_file.parent.resolve())
            payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            if args.out:
                target = Path(args.out).resolve()
                if target != record_file.resolve():
                    raise A2VError(f"模板只能写入作品记录路径：{record_file}")
                target.write_text(payload, encoding="utf-8")
                print(f"制作记录模板已写入：{target}")
            else:
                print(payload, end="")
            print("AI 助手请读取 motion-design.md 与实际评审画面，自动完成导演计划及带材料摘要的 AI 评审。")
            return 0
        if args.command == "keyframes":
            from a2v.cli import main_review
            review_args = ["--storyboard", args.storyboard, "--content-root", str(article.workspace_root)]
            result = main_review(review_args)
            if result == 0:
                production.attach_material(record_file, article, "keyframes",
                    article.output_dir / "inspect" / "contact-sheet.png", current)
            return result
        if args.command in {"samples", "rehearsal"}:
            from a2v.cli import main_render
            media_path = args.media or (str(article.media_manifest) if article.media_manifest.is_file() else None)
            if not media_path:
                raise A2VError("有声预演需要有效配音；请先运行 prepare.py 并传入 --media")
            media = __import__("a2v.media", fromlist=["load_media"]).load_media(media_path, args.storyboard)
            frame_ranges: list[tuple[int, int, list[str], list[str]]] = []
            if args.command == "samples":
                record = production.load_record(record_file, {item.id for item in model.scenes})
                frame_ranges = production.key_scene_ranges(media.storyboard.scenes,
                    record["direction"]["keyScenes"], model.fps, media.storyboard.total_frames)
                if not frame_ranges:
                    raise A2VError("制作记录没有可用的关键幕")
            else:
                frame_ranges = [(0, media.storyboard.total_frames - 1, ["全片"], ["rehearsal"])]
            manifests = []
            preview_dir = article.preview_dir / "production"
            preview_dir.mkdir(parents=True, exist_ok=True)
            for index, (first, last, scene_ids, scene_roles) in enumerate(frame_ranges, 1):
                label = "rehearsal" if args.command == "rehearsal" else f"key-scenes-{index:02d}"
                target = preview_dir / f"{label}.mp4"
                code = main_render(["--storyboard", args.storyboard, "--media", media_path,
                                   "--content-root", str(article.workspace_root), "--out", str(target),
                                   "--purpose", "review", "--frame-range", f"{first}-{last}",
                                   "--scale", "0.5", "--crf", "28"])
                if code:
                    return code
                manifests.append({"file": target.name, "startFrame": first, "endFrame": last,
                                  "sceneIds": scene_ids, "roles": scene_roles})
            manifest_path = preview_dir / f"{args.command}.json"
            manifest_path.write_text(json.dumps({"purpose": "review", "fps": model.fps,
                "totalFrames": media.storyboard.total_frames, "fingerprints": current,
                "outputs": manifests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            production.attach_material(record_file, article, args.command, manifest_path, current)
            print(f"评审材料清单：{manifest_path}")
            return 0
        if not record_file.is_file():
            print(json.dumps({"record": str(record_file), "stages": production.status_rows(None, raw, current),
                              "fingerprints": current}, ensure_ascii=False, indent=2))
            return 1
        try:
            record = production.load_record(record_file, {item.id for item in model.scenes})
        except A2VError:
            if args.command != "status":
                raise
            # Keep status useful while a creator is still filling the generated
            # template; render and sample commands continue to require a valid record.
            record = json.loads(record_file.read_text(encoding="utf-8"))
        rows = production.status_rows(record, raw, current, record_file)
        from a2v.cli import _aesthetic_render_gate
        legacy_gate = None if rows and rows[0]["stage"] == "导演规划" else _aesthetic_render_gate(
            args.storyboard, model, article, args.media
        )
        if legacy_gate:
            rows[-1]["status"] = "blocked"
            rows[-1]["detail"] = "配音媒体已过期，请重新生成媒体清单并更新动态评审" if stale_media else legacy_gate
            rows[-1]["nextCommand"] = (
                "uv run python .agents/skills/article2video/scripts/prepare.py --storyboard <分镜>"
                if stale_media else "按 review.py 输出及视觉评审量表补齐既有评审"
            )
        print(json.dumps({"record": str(record_file), "fingerprints": current,
                          "stages": rows}, ensure_ascii=False, indent=2))
        return 0 if all(row["status"] in {"passed", "not-required"} for row in rows) else 1
    except (A2VError, OSError, ValueError) as exc:
        print(f"production.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
