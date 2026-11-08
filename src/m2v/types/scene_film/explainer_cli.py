"""文章专属输入审查与候选稿操作；制作统一走 m2v。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_project
from . import explainer, explainer_review, article_text


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "sounds":
        from . import sound_library
        return sound_library.main(argv[1:])
    if argv and argv[0] == "assets":
        from . import media_assets
        return media_assets.main(argv[1:])
    parser = argparse.ArgumentParser(prog="m2v author")
    parser.add_argument("command", choices=("input-review", "candidate", "adopt-candidate", "status", "keyframes"))
    parser.add_argument("--storyboard")
    parser.add_argument("--article")
    parser.add_argument("--text-file")
    parser.add_argument("--content-root")
    args = parser.parse_args(argv)
    if not args.storyboard and not args.article:
        parser.error("需要 --storyboard 或 --article")
    # 只接受分镜路径或作品内源文；--article 允许指向作品目录之外的文本文件时无归属可推导。
    location = Path(args.storyboard or args.article).resolve()
    root = Path(args.article).resolve().parent if args.command in {"candidate", "adopt-candidate"} and args.article else location.parent
    try:
        project = None
        if (root / "project.json").is_file():
            root, project = load_project(root)

        elif args.storyboard:
            # 无 project.json 的兼容入口：以分镜所在目录为作品根，材料名固定为 storyboard.json。
            project = {"materials": {"storyboard": location.name}}
        if args.command in {"candidate", "adopt-candidate"}:
            if project is None and not args.article:
                raise M2VError("候选稿操作需要 --article 或带 project.json 的作品目录")
            _candidate(args, root, project)
            return 0
        if not args.storyboard:
            raise M2VError("该操作需要 --storyboard；只有 candidate 与 adopt-candidate 可以只用 --article")
        if project is None:
            project = {"materials": {"storyboard": location.name}}
        explainer.load(root, project)
        if args.command == "input-review":
            print(f"请阅读源文并填写讲解语义审查：{explainer_review.create_input(root, project)}")
            return 0
        from m2v.cli import main as unified
        if args.command == "keyframes":
            from m2v.standalone import executor
            from m2v.engine.lookdev import keyframes
            prepared = executor.current(root, project)
            print(json.dumps(keyframes(root, project, prepared), ensure_ascii=False))
            return 0
        command = args.command
        return unified([command, "--project", str(root)])
    except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"m2v author: {exc}", file=sys.stderr)
        return 2


def _candidate(args, root: Path, project: dict | None) -> None:
    """候选稿生成与采用：原文保持不变，采用后重新开启输入语义审查。"""
    source = root / "article.md"
    if not source.is_file() or not article_text.count_characters(article_text.extract_body(source.read_text(encoding="utf-8-sig"))):
        raise M2VError("缺少非空原文，不得编造候选稿")
    record_file = root / "outputs/candidate.json"
    candidate = root / "article.candidate.md"
    from m2v.core.delivery import digest
    if args.command == "candidate":
        if not args.text_file:
            raise M2VError("candidate 需要 --text-file")
        text = Path(args.text_file).read_text(encoding="utf-8-sig")
        if not article_text.count_characters(article_text.extract_body(text)):
            raise M2VError("候选稿必须非空")
        candidate.write_text(text, encoding="utf-8")
        _write_json(record_file, {"basedOn": digest(source), "sha256": digest(candidate)})
        print(f"候选稿已保存：{candidate}；用户明确采用后运行 adopt-candidate")
        return
    record = json.loads(record_file.read_text(encoding="utf-8"))
    if record.get("basedOn") != digest(source) or record.get("sha256") != digest(candidate):
        raise M2VError("候选稿或原文已变化，请重新生成候选")
    (root / "article.accepted.md").write_bytes(candidate.read_bytes())
    if project is not None and "article" in project["materials"]:
        project["materials"]["article"] = "article.accepted.md"
        _write_json(root / "project.json", project)
    explainer_review.create_input(root, {"materials": {"article": "article.accepted.md"}})
    print("已明确采用候选稿，请重新完成输入语义审查并 prepare")
