"""媒体评审、问题及基线的统一入口。"""

from pathlib import Path
import json

from m2v.core.project import load_project
from m2v.core.errors import M2VError
from . import ledger, reviews, issues, baselines, dependencies, media_evidence
from .storage import read, locked


def add_parsers(sub):
    review = sub.add_parser("review", help="独立媒体评审与全片预演")
    review.add_argument("action", choices=("start", "pack", "import", "timeline", "retarget", "reuse"))
    review.add_argument("--project", required=True)
    review.add_argument("--file", help="评审请求、报告或用户目标变更 JSON")
    review.add_argument(
        "--split-final", action="store_true", help="终审按结构和视觉文案分工"
    )
    review.add_argument(
        "--basis", default="常规综合终审", help="终审分工的具体风险依据"
    )
    problem = sub.add_parser("issues", help="更新唯一问题记录")
    problem.add_argument("action", choices=("update",))
    problem.add_argument("--project", required=True)
    problem.add_argument("--file", required=True)
    baseline = sub.add_parser("baseline", help="保护基线与安全清理")
    baseline.add_argument("action", choices=("create", "prune"))
    baseline.add_argument("--project", required=True)
    baseline.add_argument("--reason", default="")
    baseline.add_argument("--files", nargs="+", default=[])
    baseline.add_argument("--candidate", action="store_true")


def dispatch(args):
    root, manifest = load_project(args.project)
    with locked(root), dependencies.snapshot(), media_evidence.snapshot():
        if args.command == "baseline":
            result = (
                baselines.create(
                    root,
                    manifest,
                    reason=args.reason,
                    files=args.files,
                    reset=not args.candidate,
                )
                if args.action == "create"
                else baselines.prune(root, manifest)
            )
        elif args.command == "issues":
            issues.update(root, read(Path(args.file)))
            result = ledger.append(root, manifest, "issues-updated")
        elif args.action == "start":
            if args.split_final and args.basis == "常规综合终审":
                raise M2VError("分工终审须提供 --basis 具体风险依据")
            result = ledger.start(
                root, manifest, split_final=args.split_final, basis=args.basis
            )
        elif args.action == "timeline":
            from .timeline import build

            result = {"path": str(build(root, manifest))}
        elif args.action == "reuse":
            from . import reuse
            if not args.file:
                raise M2VError('reuse 需要 --file 完整媒体视觉复用请求')
            result = reuse.register(root, manifest, read(Path(args.file)))
        elif args.action == "retarget":
            from . import targets

            if not args.file:
                raise M2VError("retarget需要 --file 用户目标变更记录")
            result = targets.register(root, manifest, read(Path(args.file)))
        else:
            if not args.file:
                raise M2VError("pack/import 需要 --file")
            result = (
                {"path": str(reviews.package(root, manifest, read(Path(args.file))))}
                if args.action == "pack"
                else reviews.import_report(root, manifest, Path(args.file))
            )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
