"""媒体评审和问题的统一入口。"""

from pathlib import Path
import json

from m2v.core.project import load_project
from m2v.core.errors import M2VError
from . import ledger, reviews, issues, dependencies, media_evidence
from .storage import read, locked


def add_parsers(sub):
    review = sub.add_parser("review", help="独立媒体评审与全片预演")
    review.add_argument("action", choices=("start", "pack", "compare", "import", "timeline", "retarget", "reuse", "scope", "confirm-evidence"))
    review.add_argument("--project", required=True)
    review.add_argument("--file", help="评审、整片证据复核或必审窗口 JSON")
    review.add_argument("--blind-id", help="自动派生同轮对照的当前盲报告 ID")
    problem = sub.add_parser("issues", help="更新唯一问题记录")
    problem.add_argument("action", choices=("update",))
    problem.add_argument("--project", required=True)
    problem.add_argument("--file", required=True)


def dispatch(args):
    root, manifest = load_project(args.project)
    with locked(root), dependencies.snapshot(), media_evidence.snapshot():
        if args.command == "issues":
            issues.update(root, read(Path(args.file)))
            result = ledger.append(root, manifest, "issues-updated")
        elif args.action == "start":
            result = ledger.start(root, manifest)
        elif args.action in ("scope", "confirm-evidence"):
            from . import film_review

            if not args.file:
                raise M2VError(f"{args.action} 需要 --file")
            action = (film_review.register_windows if args.action == "scope"
                      else film_review.confirm_evidence)
            result = action(root, manifest, read(Path(args.file)))
        elif args.action == "timeline":
            from .timeline import build

            result = {"path": str(build(root, manifest))}
        elif args.action == "compare":
            if not args.blind_id:
                raise M2VError('compare 需要 --blind-id')
            result = reviews.package_result(root, reviews.compare(root, manifest, args.blind_id))
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
                reviews.package_result(root, reviews.package(root, manifest, read(Path(args.file))))
                if args.action == "pack"
                else reviews.import_report(root, manifest, Path(args.file))
            )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
