"""制作层命令适配；输出记录不参与 render 的技术门禁。"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.project import load_project
from . import baselines, checks, issues, ledger, reviews, workflow
from .storage import locked, read, receipt


def add_parsers(sub) -> None:
    gates = sub.add_parser('gates', help='制作门检查、证据登记及隔离评审包')
    gates.add_argument('action', choices=('check', 'register', 'rebuild', 'repair', 'pack', 'timeline'))
    gates.add_argument('--project', required=True)
    gates.add_argument('--gate', choices=workflow.GATE_IDS)
    gates.add_argument('--checkpoint')
    gates.add_argument('--file')
    issues_parser = sub.add_parser('issues', help='更新唯一问题表机器块')
    issues_parser.add_argument('action', choices=('update',))
    issues_parser.add_argument('--project', required=True)
    issues_parser.add_argument('--file', required=True)
    baseline = sub.add_parser('baseline', help='创建重置/候选基线，或安全清理媒体')
    baseline.add_argument('action', choices=('create', 'prune'))
    baseline.add_argument('--project', required=True)
    baseline.add_argument('--reason', default='')
    baseline.add_argument('--files', nargs='+', default=[])
    baseline.add_argument('--candidate', action='store_true', help='局部候选保护，不计为重置')


def dispatch(args) -> int:
    root, manifest = load_project(args.project)
    if manifest['type'] != 'general':
        raise M2VError('制作门仅适用于 general；专用类型维持原契约')
    with locked(root):
        if args.command == 'issues':
            issues.update(root, read(Path(args.file)))
            result = ledger.append(root, manifest, 'issues-updated', evidence=[receipt(outputs(root), outputs(root) / 'visual-notes.md')])
        elif args.command == 'baseline':
            result = baselines.create(root, manifest, reason=args.reason, files=args.files, reset=not args.candidate) if args.action == 'create' else baselines.prune(root, manifest)
        elif args.command == 'review':
            if not args.file:
                raise M2VError('review import 需要 --file 独立评审报告')
            result = reviews.import_report(root, manifest, Path(args.file).resolve())
        elif args.action == 'repair':
            result = ledger.repair(root)
        elif args.action == 'rebuild':
            result = ledger.rebuild(root, manifest)
        elif args.action == 'pack':
            if not args.file:
                raise M2VError('pack 需要 --file 评审包请求 JSON')
            result = {'path': str(reviews.package(root, **read(Path(args.file))))}
        elif args.action == 'timeline':
            from .timeline import build
            result = {'path': str(build(root, manifest))}
        elif args.action == 'register':
            if not args.file:
                raise M2VError('register 需要 --file 检查报告')
            result = ledger.register(root, manifest, Path(args.file).resolve())
        else:
            if not args.gate:
                raise M2VError('check 需要 --gate')
            paths = checks.run(root, manifest, args.gate, checkpoint_id=args.checkpoint)
            result = {'reports': [str(p) for p in paths], 'events': [ledger.register(root, manifest, p)['id'] for p in paths]}
        if args.command != 'gates' or args.action not in ('repair', 'rebuild'):
            ledger.rebuild(root, manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
