"""``m2v author assets`` 的素材工作流路由：discover/fetch/index/find/preview/select/library/models/doctor。

这里只解析参数、调度服务并映射退出码：0 全部成功（允许零命中），1 部分成功，
2 参数/契约错误或全部失败，130 取消。旧 search/import 行为保持不变。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .contracts import CandidateData, Requirement, parse_collection, parse_document
from .errors import MaterialError
from .store import MaterialStore, workspace_root


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _failures(code: int, message: str, *, stage='cli') -> int:
    print(_json({'ok': False, 'error': {'code': code, 'stage': stage, 'message': message}}),
          file=sys.stderr)
    return 130 if code == 'cancelled' else 2


def _root(args) -> Path:
    project = getattr(args, 'project', None)
    workspace = getattr(args, 'workspace', None)
    if project:
        root = Path(project).expanduser()
        if not (root / 'project.json').is_file():
            raise MaterialError('not-found', '--project 不是有效作品目录（缺少 project.json）', stage='cli')
        return workspace_root(project=root)
    return workspace_root(workspace=Path(workspace).expanduser() if workspace else None)


def _models(args, root: Path):
    from .model_manager import ModelManager
    path = Path(args.models_dir).expanduser() if getattr(args, 'models_dir', None) else root / 'models'
    return ModelManager(path)


def _emit(args, value: str | dict, human: str) -> None:
    if getattr(args, 'json', False):
        print(value if isinstance(value, str) else _json(value))
    else:
        print(human)


def _discover(args) -> int:
    from .discovery import discover, providers
    from .platform import platform_providers, register_link
    from .registration import register_url
    from .network import SafeHTTP, NetworkBudget
    requirements = []
    for path in args.request or []:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(value, dict) and 'data' in value and value.get('kind') == 'material.requirement':
            requirements.append(parse_document(value))
        else:
            collection = parse_collection(value)
            requirements.extend(item for item in collection.data if isinstance(item, Requirement))
        if not all(isinstance(item, Requirement) for item in requirements):
            raise MaterialError('invalid-request', '--request 只接受需求文档或需求集合', stage='discover')
    selected = list(args.provider or ())
    if not selected:
        selected = ['commons', 'archive', 'nasa']
        if os.environ.get('PIXABAY_API_KEY') or os.environ.get('PIXABAY_KEY'):
            selected.append('pixabay')
    http = SafeHTTP(NetworkBudget(max_bytes=min(args.max_bytes, 16 * 1024 * 1024), total_bytes=args.max_bytes,
                                  max_requests=128, timeout_s=args.timeout, deadline_s=args.timeout * 4))
    table = providers(http)
    from .platform import SEARCH_PROVIDERS
    for name in selected:
        if name in SEARCH_PROVIDERS and name not in table:
            table[name] = platform_providers(worker=None, cookies=args.cookies,
                                             timeout_s=args.timeout)[list(SEARCH_PROVIDERS).index(name)]
    chosen = []
    for name in selected:
        if name not in table:
            raise MaterialError('unsupported-source', f'未知来源 {name}', stage='discover')
        chosen.append(table[name])
    from .contracts import Query
    queries = [Query(text=value) for value in (args.query or [])]
    root = _root(args)
    with MaterialStore(root) as store:
        explicit = []
        for url in args.url or []:
            registered = register_url(url, store=store, mode=args.url_mode)
            explicit.append(registered.document)
        for url in args.platform_link or []:
            document, _ = register_link(store, url, title=args.title)
            explicit.append(document)
        result = discover(selected=chosen, requirements=requirements, queries=queries, store=store,
                          kind=args.kind, page_size=args.page_size, max_pages=args.max_pages,
                          max_results=args.max_results)
        payload = result.to_dict()
        if explicit:
            payload['explicit'] = [item.model_dump(mode='json') for item in explicit]
            payload['sources'] = [*payload['sources'], *[item.model_dump(mode='json') for item in explicit]]
    _emit(args, payload, f"发现 {len(payload['sources'])} 个来源；失败 {len(payload['failures'])}；退出码 {payload['exitCode']}")
    return result.exit_code if not explicit else max(result.exit_code, 0)


def _range(value: str | None):
    if not value:
        return None
    from .contracts import TimeRange
    try:
        left, right = value.split('-', 1)
        start, end = float(left), float(right)
    except (ValueError, AttributeError):
        raise MaterialError('invalid-request', '--range 必须为 START-END 秒', stage='fetch') from None
    if not 0 <= start < end:
        raise MaterialError('invalid-request', '--range 起点必须小于终点', stage='fetch')
    return TimeRange(startUs=round(start * 1_000_000), endUs=round(end * 1_000_000))


def _fetch(args) -> int:
    from .fetch import FetchBudget, fetch_page, fetch_platform, fetch_local, fetch_public_file, fetch_source
    from .platform import provider_for, register_link
    from .registration import register_local, register_url
    budget = FetchBudget(max_bytes=args.max_bytes, max_duration_us=int(args.max_seconds * 1_000_000))
    interval = _range(args.range)
    root = _root(args)
    results, failures = [], []
    with MaterialStore(root) as store:
        operations = [('source', item) for item in (args.source or [])]
        operations += [('local', item) for item in (args.local or [])]
        operations += [('url', item) for item in (args.url or [])]
        if not operations:
            raise MaterialError('invalid-request', 'fetch 需要 --source、--local 或 --url', stage='fetch')
        for kind, value in operations:
            try:
                if kind == 'source':
                    source = store.get(value, kind='material.source')
                    fetched = fetch_source(store, source=source, locator=args.locator,
                                           budget=budget, format_id=args.format,
                                           subtitles=not args.no_subtitles, cookies=args.cookies,
                                           requested_range=interval)
                elif kind == 'local':
                    registered = register_local(value, store=store, title=args.title,
                                                author=args.author, license=args.license)
                    fetched = fetch_local(store, source=registered.document, path=Path(value), budget=budget,
                                          requested_range=interval)
                else:
                    try:
                        provider_for(value)
                    except MaterialError:
                        mode = args.url_mode
                        if mode == 'auto':
                            from urllib.parse import urlsplit
                            from .fetch import MEDIA_SUFFIXES
                            mode = 'file' if Path(urlsplit(value).path).suffix.lower() in MEDIA_SUFFIXES else 'page'
                        registered = register_url(value, store=store, mode=mode, title=args.title,
                                                  author=args.author, license=args.license)
                        if mode == 'file':
                            fetched = fetch_public_file(store, source=registered.document, url=value,
                                                        budget=budget, requested_range=interval)
                        else:
                            fetched = fetch_page(store, source=registered.document, url=value,
                                                 budget=budget, requested_range=interval)
                    else:
                        document, locator = register_link(store, value, title=args.title,
                                                          author=args.author, license=args.license)
                        fetched = fetch_platform(store, source=document, url=locator, budget=budget,
                                                 format_id=args.format, subtitles=not args.no_subtitles,
                                                 cookies=args.cookies, requested_range=interval)
                results.append({'media': fetched.media.model_dump(mode='json'),
                                'warnings': fetched.warnings, 'stats': fetched.stats})
            except MaterialError as exc:
                failures.append({'input': kind, 'error': exc.to_dict()})
    payload = {'schemaVersion': 1, 'results': results, 'failures': failures}
    _emit(args, payload, f'获取完成 {len(results)} 项，失败 {len(failures)} 项')
    if failures:
        return 1 if results else 2
    return 0


def _index(args) -> int:
    from . import indexing
    manager = _models(args, _root(args))
    options = {'shots': {'threshold': args.threshold, 'adaptive': args.adaptive,
                         'long_shot_s': args.long_shot, 'max_frames': args.max_frames},
               'asr': {'language': args.asr_language, 'vad': not args.no_vad,
                       'beam_size': args.beam_size, 'device': args.device},
               'ocr': {'max_frames': args.max_frames},
               'text': {'batch_size': args.batch_size},
               'visual': {'max_frames': args.max_frames}}
    channels = args.channel or ['captions', 'chapters', 'shots', 'frames']
    root = _root(args)
    results, failures = [], []
    with MaterialStore(root) as store:
        for media_id in args.media:
            try:
                media = store.get(media_id, kind='material.media')
            except MaterialError as exc:
                failures.append({'mediaId': media_id, 'error': exc.to_dict()})
                continue
            for channel in channels:
                try:
                    results.extend(row.to_dict() for row in
                                   indexing.index_media(store, media, manager, [channel], options=options))
                except MaterialError as exc:
                    if exc.code in {'not-found'} and args.tolerate_missing:
                        results.append({'mediaId': media.id, 'channel': channel, 'status': 'skipped',
                                        'reason': exc.code})
                    else:
                        failures.append({'mediaId': media.id, 'channel': channel, 'error': exc.to_dict()})
    payload = {'schemaVersion': 1, 'indexes': results, 'failures': failures}
    _emit(args, payload, f'索引 {len(results)} 项，失败 {len(failures)} 项')
    if failures:
        return 1 if results else 2
    return 0


def _load_requirement(path: str) -> Requirement:
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    document = parse_document(value)
    if not isinstance(document, Requirement):
        raise MaterialError('invalid-request', '--requirement 必须是需求文档', stage='find')
    return document


def _find(args) -> int:
    from .retrieval import find
    requirement = _load_requirement(args.requirement) if args.requirement else None
    channels = args.channel or ['lexical', 'metadata']
    manager = _models(args, _root(args)) if ({'text', 'visual'} & set(channels)) else None
    root = _root(args)
    with MaterialStore(root) as store:
        result = find(store, query=args.query, requirement=requirement, manager=manager,
                      channels=channels, top_k=args.top_k,
                      context_us=int(args.context * 1_000_000),
                      merge_gap_us=int(args.merge_gap * 1_000_000),
                      media_ids=args.media or None,
                      orientation=args.orientation,
                      min_duration_us=int(args.min_seconds * 1_000_000),
                      provider=args.provider_filter)
    payload = result.to_dict()
    payload['hint'] = ('零命中可能表示缺索引或索引与该媒体不兼容；请先运行 index，'
                       'find 不会自动获取或建立索引')
    if args.out:
        Path(args.out).write_text(_json(payload) + '\n', encoding='utf-8')
    _emit(args, payload, f"候选 {len(result.candidates)} 个；通道命中 {result.channels}")
    return 0


def _candidates(path: str) -> list[CandidateData]:
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(value, dict) and 'candidates' in value:
        value = value['candidates']
    return [CandidateData.model_validate(item) for item in value]


def _preview(args) -> int:
    from .preview import preview_candidates
    candidates = _candidates(args.candidates)
    if args.index:
        if not 1 <= args.index <= len(candidates):
            raise MaterialError('invalid-request', '--index 超出候选数量', stage='preview')
        candidates = [candidates[args.index - 1]]
    root = _root(args)
    with MaterialStore(root) as store:
        result = preview_candidates(store, candidates, out=root / 'previews' / (args.out or 'latest'),
                                    columns=args.columns, tile_width=args.tile_width,
                                    preview_seconds=args.preview_seconds, html_output=not args.no_html)
    payload = {'schemaVersion': 1, 'directory': str(result.directory),
               'sheet': str(result.sheet) if result.sheet else None,
               'html': str(result.html) if result.html else None, 'candidates': result.candidates}
    _emit(args, payload, f'预览输出：{result.directory}')
    return 0


def _select(args) -> int:
    from .contracts import Transform
    from .import_work import import_selection
    from .selection import persist_candidate, select
    candidates = _candidates(args.candidates)
    if args.index:
        if not 1 <= args.index <= len(candidates):
            raise MaterialError('invalid-request', '--index 超出候选数量', stage='select')
        candidates = [candidates[args.index - 1]]
    if len(candidates) != 1:
        raise MaterialError('invalid-request', 'select 需要 --index 指定单个候选', stage='select')
    transform = Transform(fps={'num': args.fps, 'den': 1}, audio=args.audio, crf=args.crf)
    root = _root(args)
    with MaterialStore(root) as store:
        candidate = persist_candidate(store, candidates[0], args.candidate_id)
        cut = select(store, candidate, decision=args.decision, rationale=args.rationale,
                     purpose=args.purpose, operator=args.operator, output_dir=root / 'selections',
                     transform=transform)
        receipt = None
        if args.import_into:
            if not args.asset_id:
                raise MaterialError('invalid-request', '--import 需要 --asset-id', stage='select')
            receipt = import_selection(store, project_root=Path(args.import_into), selection_id=cut.selection.id,
                                       asset_id=args.asset_id, role=args.role, replace=args.replace)
    payload = {'schemaVersion': 1, 'selection': cut.selection.model_dump(mode='json'),
               'measured': cut.measured,
               'receipt': receipt.receipt.model_dump(mode='json') if receipt else None}
    _emit(args, payload, f"选择 {cut.selection.id}；精裁误差 {cut.measured or '图片或未精裁'}"
          + (f'；已导入 {receipt.entry.get("path")}' if receipt else ''))
    return 0


def _library(args) -> int:
    from . import library
    root = _root(args)
    with MaterialStore(root) as store:
        if args.action == 'scan':
            if not args.dir:
                raise MaterialError('invalid-request', 'library scan 需要 --dir', stage='library')
            from .fetch import FetchBudget
            result = library.scan_directory(store, Path(args.dir), recursive=args.recursive,
                                            budget=FetchBudget(max_bytes=args.max_bytes), max_files=args.max_files,
                                            retry_failed=args.retry_failed)
        elif args.action == 'verify':
            result = library.verify_library(store)
        elif args.action == 'stats':
            result = library.stats(store)
        elif args.action == 'cleanup-plan':
            result = library.cleanup_plan(store)
        else:
            if not args.digest:
                raise MaterialError('invalid-request', 'cleanup-apply 需要 --digest', stage='library')
            result = library.apply_cleanup(store, args.digest)
    _emit(args, result, _json(result))
    if isinstance(result, dict) and result.get('failures'):
        return 1 if result.get('files') else 2
    return 0 if not (isinstance(result, dict) and result.get('issues')) else 1


def _models_workflow(args) -> int:
    manager = _models(args, _root(args))
    if args.action == 'list':
        result = {'models': manager.list(), 'registryDigest': manager.registry_digest}
        _emit(args, result, _json(result))
        return 0
    names = args.name or list(manager.registry['models'])
    results, failures = [], []
    for name in names:
        try:
            results.append(manager.verify(name) if args.action == 'verify'
                           else manager.prepare(name, repair=args.repair))
        except MaterialError as exc:
            failures.append({'name': name, 'error': exc.to_dict()})
    payload = {'action': args.action, 'results': results, 'failures': failures}
    _emit(args, payload, f'{args.action} 完成 {len(results)} 项，失败 {len(failures)} 项')
    if failures:
        return 1 if results else 2
    return 0


def _doctor(args) -> int:
    from .diagnostics import doctor
    root = _root(args)
    result = doctor(Path(args.models_dir).expanduser() if args.models_dir else root / 'models')
    _emit(args, result, _json(result))
    return 0


def _common(parser, *, project_required=False):
    parser.add_argument('--project', required=project_required, help='作品目录；默认工作根为 <project>/outputs/materials')
    parser.add_argument('--workspace', help='无作品时显式素材工作根')
    parser.add_argument('--json', action='store_true', help='输出 JSON')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='m2v author assets', description='素材发现、获取、索引、检索、预览、选择与复用')
    sub = parser.add_subparsers(dest='workflow', required=True)

    item = sub.add_parser('discover', help='多需求/多来源发现；不下载视频')
    _common(item)
    item.add_argument('--request', action='append', help='需求文档或需求集合 JSON，可重复')
    item.add_argument('--query', action='append', help='独立关键词查询，可重复')
    item.add_argument('--provider', action='append', help='commons/archive/nasa/pixabay/youtube/bilibili')
    item.add_argument('--kind', default='video', choices=('video', 'image', 'audio', 'any'))
    item.add_argument('--page-size', type=int, default=20)
    item.add_argument('--max-pages', type=int, default=2)
    item.add_argument('--max-results', type=int, default=200)
    item.add_argument('--max-mb', dest='max_bytes', type=int, default=512)
    item.add_argument('--timeout', type=float, default=30.0)
    item.add_argument('--url', action='append', help='显式网页/文件候选，可重复')
    item.add_argument('--url-mode', default='auto', choices=('page', 'file', 'auto'))
    item.add_argument('--platform-link', action='append', help='抖音/小红书/微博/西瓜已知链接')
    item.add_argument('--cookies', help='平台专用 Netscape cookie 文件')
    item.add_argument('--title')
    item.set_defaults(handler=_discover)

    item = sub.add_parser('fetch', help='受控获取本地/公开/平台媒体')
    _common(item)
    item.add_argument('--source', action='append', help='已登记来源 ID，可重复')
    item.add_argument('--locator', help='本地来源重新获取时的原文件；或页面/直链的显式地址')
    item.add_argument('--local', action='append', help='显式本地媒体，可重复')
    item.add_argument('--url', action='append', help='公开网页、直链或平台分享链接，可重复')
    item.add_argument('--url-mode', default='auto', choices=('page', 'file', 'auto'))
    item.add_argument('--range', help='请求区间 START-END 秒；先完整获取再本地精裁')
    item.add_argument('--format', default='best', help='平台格式 ID 或 best')
    item.add_argument('--no-subtitles', action='store_true')
    item.add_argument('--cookies', help='平台专用 Netscape cookie 文件')
    item.add_argument('--max-mb', dest='max_bytes', type=int, default=1024)
    item.add_argument('--max-seconds', type=float, default=6 * 3600)
    item.add_argument('--title')
    item.add_argument('--author')
    item.add_argument('--license')
    item.set_defaults(handler=_fetch)

    item = sub.add_parser('index', help='离线建立字幕/转录/镜头/OCR/文本/视觉索引')
    _common(item)
    item.add_argument('--media', action='append', required=True, help='媒体 ID，可重复')
    item.add_argument('--channel', action='append',
                      choices=('captions', 'chapters', 'shots', 'frames', 'asr', 'ocr', 'text', 'visual'))
    item.add_argument('--models', dest='models_dir')
    item.add_argument('--threshold', type=float, default=0.3)
    item.add_argument('--adaptive', action='store_true')
    item.add_argument('--long-shot', type=float, default=10.0)
    item.add_argument('--max-frames', type=int, default=48)
    item.add_argument('--asr-language')
    item.add_argument('--no-vad', action='store_true')
    item.add_argument('--beam-size', type=int, default=5)
    item.add_argument('--device', choices=('cpu', 'cuda'), default='cpu',
                      help='转录设备；CUDA 只在显式选择时使用，默认 CPU int8')
    item.add_argument('--batch-size', type=int, default=16)
    item.add_argument('--tolerate-missing', action='store_true',
                      help='没有字幕/章节时记为 skipped 而不是失败')
    item.set_defaults(handler=_index)

    item = sub.add_parser('find', help='只查询显式范围内的有效索引')
    _common(item)
    item.add_argument('--query')
    item.add_argument('--requirement', help='需求文档 JSON')
    item.add_argument('--channel', action='append', choices=('lexical', 'text', 'visual', 'metadata'))
    item.add_argument('--top-k', type=int, default=10)
    item.add_argument('--context', type=float, default=0.0, help='候选窗口上下扩展秒数')
    item.add_argument('--merge-gap', type=float, default=1.0, help='同源相邻窗口合并秒数')
    item.add_argument('--media', action='append', help='限定媒体 ID，可重复')
    item.add_argument('--orientation', choices=('landscape', 'portrait', 'square'), help='按画幅过滤')
    item.add_argument('--min-seconds', type=float, default=0.0, help='最短媒体时长过滤')
    item.add_argument('--provider-filter', help='只查指定来源，例如 commons/nasa/local')
    item.add_argument('--models', dest='models_dir')
    item.add_argument('--out', help='把完整 JSON 写入文件')
    item.set_defaults(handler=_find)

    item = sub.add_parser('preview', help='候选接触表、短预览与静态 HTML')
    _common(item)
    item.add_argument('--candidates', required=True, help='find 输出的 JSON')
    item.add_argument('--index', type=int, help='只预览第 N 个候选（从 1 开始）')
    item.add_argument('--out', default=None, help='工作根下的子目录名')
    item.add_argument('--columns', type=int, default=3)
    item.add_argument('--tile-width', type=int, default=480)
    item.add_argument('--preview-seconds', type=float, default=6.0)
    item.add_argument('--no-html', action='store_true')
    item.set_defaults(handler=_preview)

    item = sub.add_parser('select', help='选择并精裁；显式 --import 才修改作品')
    _common(item)
    item.add_argument('--candidates', required=True, help='find 或 preview 的候选 JSON')
    item.add_argument('--index', type=int, help='候选序号（从 1 开始）')
    item.add_argument('--candidate-id', help='持久化候选时使用的显式 ID')
    item.add_argument('--decision', choices=('chosen', 'rejected'), default='chosen')
    item.add_argument('--rationale', required=True)
    item.add_argument('--purpose', required=True)
    item.add_argument('--operator', required=True)
    item.add_argument('--fps', type=int, default=30)
    item.add_argument('--audio', choices=('preserve', 'discard'), default='preserve')
    item.add_argument('--crf', type=int, default=18)
    item.add_argument('--import', dest='import_into', metavar='PROJECT', help='导入目标作品目录')
    item.add_argument('--asset-id')
    item.add_argument('--role', default='color')
    item.add_argument('--replace', action='store_true')
    item.set_defaults(handler=_select)

    item = sub.add_parser('library', help='显式目录登记、核验、统计与安全清理')
    _common(item)
    item.add_argument('action', choices=('scan', 'verify', 'stats', 'cleanup-plan', 'cleanup-apply'))
    item.add_argument('--dir', help='scan 的显式目录')
    item.add_argument('--recursive', action='store_true')
    item.add_argument('--max-files', type=int, default=500, help='每轮新的获取尝试预算；重复扫描复用已完成项')
    item.add_argument('--retry-failed', action='store_true', help='重试内容未变化的已失败项')
    item.add_argument('--max-mb', dest='max_bytes', type=int, default=1024)
    item.add_argument('--digest', help='cleanup-apply 的计划摘要')
    item.set_defaults(handler=_library)

    item = sub.add_parser('models', help='显式模型准备与校验')
    _common(item)
    item.add_argument('action', choices=('list', 'prepare', 'verify'))
    item.add_argument('--name', action='append')
    item.add_argument('--repair', action='store_true')
    item.add_argument('--models', dest='models_dir')
    item.set_defaults(handler=_models_workflow)

    item = sub.add_parser('doctor', help='工具/设备/运行库/模型/来源诊断')
    _common(item)
    item.add_argument('--models', dest='models_dir')
    item.set_defaults(handler=_doctor)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if getattr(args, 'max_bytes', None):
        args.max_bytes = int(args.max_bytes) * 1024 * 1024
    try:
        return args.handler(args)
    except MaterialError as exc:
        return _failures(exc.code, str(exc), stage=exc.stage)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _failures('invalid-request', f'素材工作流参数或材料错误：{exc}')
