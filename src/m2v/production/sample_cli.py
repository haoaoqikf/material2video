"""原生样品CLI；保存失败候选和交付检查是不同操作。"""
import json
import threading
from pathlib import Path
from m2v.core.project import load_project
from . import dependencies, media_evidence, reviews, samples
from .storage import local, locked, read


def add_parser(sub):
    parser = sub.add_parser('sample', help='网页原生设计样品：采集、播放和独立通过后交付')
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('capture', 'serve', 'review', 'deliver'):
        action = actions.add_parser(name)
        action.add_argument('--project', required=True)
        if name == 'capture':
            action.add_argument('--entry', required=True, help='作品scenes/下TSX入口')
            action.add_argument('--props', help='作品内JSON参数文件，不需要完整分镜')
            action.add_argument('--duration-seconds', type=float, required=True)
            action.add_argument('--kind', choices=('static', 'motion'), default='static', help='默认静态，只采集网页及关键帧；motion另编码过程')
            action.add_argument('--frame', type=int, action='append', dest='still_frames', help='幕内取帧位置，可重复；省略为末帧')
        else:
            action.add_argument('--id', required=True, help='sample capture返回的ID')
        if name == 'serve':
            action.add_argument('--port', type=int, default=0)
        if name == 'review':
            action.add_argument('--purpose', choices=('keyframe',), default='keyframe')
            action.add_argument('--targets', required=True, help='实际参考与中性条件JSON；工具自动派生来源和观察窗口')
        if name == 'deliver':
            action.add_argument('--blind-id', required=True)
            action.add_argument('--comparison-id', required=True)
            action.add_argument('--basis', required=True, help='当前样品达到原定目标的具体选案依据')


def dispatch(args):
    root, project = load_project(args.project)
    if args.action == 'serve':
        with samples.server(root, project, args.id, port=args.port) as server:
            print(json.dumps({'url': server.base_url + '/index.html'}, ensure_ascii=False), flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                return 0
    with locked(root), dependencies.snapshot(), media_evidence.snapshot():
        if args.action == 'capture':
            props = read(local(root, args.props)) if args.props else {}
            result = samples.capture(root, project, entry=args.entry, props=props,
                                     duration_seconds=args.duration_seconds, still_frames=args.still_frames,
                                     props_source=args.props, kind=args.kind)
        elif args.action == 'review':
            result = reviews.package_result(root, samples.review(root, project, args.id, targets=read(Path(args.targets))))
        else:
            result = samples.deliver(root, project, args.id, blind_id=args.blind_id,
                                     comparison_id=args.comparison_id, basis=args.basis)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
