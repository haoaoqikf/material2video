"""Article-specific production records and review-material workflow."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from a2v.core.errors import A2VError
from a2v.types.article import article_text, paths, production, storyboard_v4
from a2v.types.article.cli import _aesthetic_render_gate, _force_utf8_output, _v4_model, main_render, main_review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2v article", description="文章类型语义审查、制作记录与评审材料")
    parser.add_argument("command", choices=("status", "template", "input-review", "candidate", "adopt-candidate", "keyframes", "samples", "rehearsal"))
    parser.add_argument("--storyboard")
    parser.add_argument("--article")
    parser.add_argument("--media")
    parser.add_argument("--content-root")
    parser.add_argument("--out")
    parser.add_argument("--text-file")
    parser.add_argument("--check-determinism", action="store_true",
                        help="对结尾帧执行同帧重复与随机寻帧检查（PSNR ≥ 60 dB）")
    args = parser.parse_args(argv)
    input_commands = {"input-review", "candidate", "adopt-candidate"}
    if not args.storyboard and not args.article:
        parser.error("必须提供 --storyboard；输入审查命令也可使用 --article")
    if args.command not in input_commands and not args.storyboard:
        parser.error(f"{args.command} 命令需要 --storyboard")
    _force_utf8_output()
    try:
        location = args.storyboard or args.article
        article = paths.for_storyboard(location, args.content_root)
        raw = json.loads(Path(args.storyboard).read_text(encoding="utf-8")) if args.storyboard else {"stages": []}
        if args.media is None and args.command != "keyframes" and article.media_manifest.is_file():
            args.media = str(article.media_manifest)
        model = None
        if args.storyboard:
            report = storyboard_v4.validate(raw)
            model = _v4_model(raw) if report.ok else None
            if model is None:
                raise A2VError("分镜校验失败：" + "; ".join(item.format() for item in report.errors))
        record_file = production.record_path(article)
        if args.command == "input-review":
            source = article_text.active_source(article.source_dir)
            if not source.is_file():
                raise A2VError(f"缺少输入文章：{source}")
            review = article_text.review_for_file(source, article.workspace_root)
            if record_file.is_file():
                record = json.loads(record_file.read_text(encoding="utf-8"))
            else:
                record = production.initialize_template(raw, {"input": review["source"]["sha256"]}, review)
                record["materialRoot"] = os.path.relpath(article.workspace_root.resolve(), record_file.parent.resolve())
            record["inputReview"] = review
            record.setdefault("fingerprints", {})["input"] = review["source"]["sha256"]
            record_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = record_file.with_suffix(record_file.suffix + ".tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(record_file)
            print(json.dumps({"record": str(record_file), "inputReview": review}, ensure_ascii=False, indent=2))
            print("请阅读原文，在 production.json 中补充 singleScene 和 assessment；语义评审保持人工完成。")
            return 0
        if args.command in {"candidate", "adopt-candidate"}:
            if not record_file.is_file():
                raise A2VError("尚无输入审查记录；请先运行 a2v article input-review")
            record = json.loads(record_file.read_text(encoding="utf-8"))
            review = record.get("inputReview") or {}
            adoption = record.get("inputAdoption")
            original = article.source_dir / "article.md"
            original_text, original_digest = article_text.read_source(original)
            candidate = article.source_dir / "article.candidate.md"
            if args.command == "candidate":
                if not article_text.count_characters(article_text.extract_body(original_text)):
                    raise A2VError("原文没有可审查正文；不得编造候选稿")
                if not args.text_file:
                    raise A2VError("candidate 命令需要 --text-file")
                info = article_text.save_candidate(article.source_dir, Path(args.text_file).read_text(encoding="utf-8"), original_digest)
                review["candidate"] = info
                record["inputReview"] = review
                record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(info, ensure_ascii=False, indent=2))
            else:
                reviewed_source = review.get("source") if isinstance(review.get("source"), dict) else {}
                re_adoption = (isinstance(adoption, dict)
                               and str(reviewed_source.get("path", "")).endswith("article.accepted.md"))
                info = adoption.get("candidate") if re_adoption else review.get("candidate")
                expected_base = adoption.get("basedOn") if re_adoption else (info or {}).get("basedOn")
                if not isinstance(info, dict) or not candidate.is_file() or expected_base != original_digest:
                    raise A2VError("没有绑定当前原文的有效候选稿")
                text, digest = article_text.read_source(candidate)
                if (not re_adoption and digest != info.get("sha256")) or not 130 <= article_text.count_characters(article_text.extract_body(text)) <= 170:
                    raise A2VError("候选稿已变化或不满足130～170字")
                accepted = article.source_dir / "article.accepted.md"
                accepted.write_text(text, encoding="utf-8")
                updated = article_text.review_for_file(accepted, article.workspace_root)
                record["inputReview"] = updated
                record.setdefault("fingerprints", {})["input"] = updated["source"]["sha256"]
                record["inputAdoption"] = {"candidate": {"path": candidate.relative_to(article.workspace_root).as_posix(), "sha256": digest},
                    "accepted": {"path": accepted.relative_to(article.workspace_root).as_posix(), "sha256": updated["source"]["sha256"]},
                    "basedOn": original_digest, "confirmation": {"source": "explicit-user-adoption", "evidence": "显式采用候选稿"}}
                record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"采用稿已保存：{accepted}；请重新完成输入语义审查")
            return 0
        current = production.current_fingerprints(args.storyboard, args.media, article)
        if args.command == "template":
            active = article_text.active_source(article.source_dir)
            input_review = article_text.review_for_file(active, article.workspace_root) if active.is_file() else None
            record = production.initialize_template(raw, current, input_review)
            record["materialRoot"] = os.path.relpath(article.workspace_root.resolve(), record_file.parent.resolve())
            payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            target = Path(args.out).resolve() if args.out else record_file
            if target != record_file.resolve():
                raise A2VError(f"模板只能写入作品记录路径：{record_file}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
            print(f"待填写模板：{target}")
            return 0
        if args.command == "keyframes":
            review_args = ["--storyboard", args.storyboard, "--content-root", str(article.workspace_root)]
            if args.check_determinism:
                review_args.append("--check-determinism")
            result = main_review(review_args)
            if result == 0:
                production.attach_material(record_file, article, "keyframes", article.output_dir / "inspect" / "contact-sheet.png", current)
            return result
        if args.command in {"samples", "rehearsal"}:
            media_path = args.media or (str(article.media_manifest) if article.media_manifest.is_file() else None)
            if not media_path:
                raise A2VError("有声预演需要配音材料；请先 prepare")
            from a2v.types.article.media import load_media
            media = load_media(media_path, args.storyboard)
            if args.command == "samples":
                record = production.load_record(record_file, {item.id for item in model.scenes})
                ranges = production.key_scene_ranges(media.storyboard.scenes, record["direction"]["keyScenes"], model.fps, media.storyboard.total_frames)
            else:
                ranges = [(0, media.storyboard.total_frames - 1, ["全片"], ["rehearsal"])]
            outputs = []
            directory = article.preview_dir / "production"
            directory.mkdir(parents=True, exist_ok=True)
            for index, (first, last, ids, roles) in enumerate(ranges, 1):
                label = "rehearsal" if args.command == "rehearsal" else f"key-scenes-{index:02d}"
                target = directory / f"{label}.mp4"
                code = main_render(["--storyboard", args.storyboard, "--media", media_path, "--content-root", str(article.workspace_root),
                    "--out", str(target), "--purpose", "review", "--frame-range", f"{first}-{last}", "--scale", "0.5", "--crf", "28"])
                if code:
                    return code
                outputs.append({"file": target.name, "startFrame": first, "endFrame": last, "sceneIds": ids, "roles": roles})
            manifest = directory / f"{args.command}.json"
            manifest.write_text(json.dumps({"purpose": "review", "fps": model.fps, "totalFrames": media.storyboard.total_frames,
                "fingerprints": current, "outputs": outputs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            production.attach_material(record_file, article, args.command, manifest, current)
            print(f"评审材料清单：{manifest}")
            return 0
        if not record_file.is_file():
            print(json.dumps({"record": str(record_file), "stages": production.status_rows(None, raw, current)}, ensure_ascii=False, indent=2))
            return 1
        record = production.load_record(record_file, {item.id for item in model.scenes})
        rows = production.status_rows(record, raw, current, record_file)
        legacy = _aesthetic_render_gate(args.storyboard, model, article, args.media)
        if legacy:
            rows[-1].update(status="blocked", detail=legacy)
        print(json.dumps({"record": str(record_file), "fingerprints": current, "stages": rows}, ensure_ascii=False, indent=2))
        return 0 if production.all_stages_pass(rows) else 1
    except (A2VError, OSError, ValueError, KeyError) as exc:
        print(f"a2v article: {exc}", file=sys.stderr)
        return 2
