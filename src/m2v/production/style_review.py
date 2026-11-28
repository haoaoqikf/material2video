"""按候选窗口解析生效风格，并在同轮对照阶段封存实际参考。"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from m2v.core import style_binding as styles
from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.materials.network import SafeHTTP
from . import dependencies
from .storage import local, write


def _scenes(root, project, request, film, overrides):
    if film:
        from .film_review import prepared
        scenes = prepared(root, project)['props']['compiledScenes']
        return {key: [s['id'] for s in scenes if s['endFrame'] > value['window'][0]
                      and s['startFrame'] < value['window'][1]] for key, value in film.items()}
    selected = request['sceneIds']
    if not selected and any(o["scope"]["scenes"] != "all" for o in overrides):
        board = styles.read_object(root, project['materials']['storyboard'])
        selected = [s['id'] for s in board['scenes']
                    if s.get('content', {}).get('entry') in request['sources']]
    return {item['id']: selected for item in request['items']}


def _references(binding, scene):
    default = binding['visualStyle']
    changes = [item for item in binding['overrides']
               if item['scope']['scenes'] == 'all' or scene in item['scope']['scenes']]
    if not changes:
        return [(default, ref) for ref in default['references']]
    change, = changes
    uses = change['scope']['uses']
    target = change['target']
    if uses == 'all':
        return [(target, ref) for ref in target['references']]
    roles = {ref['role'] for ref in default['references'] if ref['id'] in uses}
    kept = [(default, ref) for ref in default['references'] if ref['id'] not in uses]
    return kept + [(target, ref) for ref in target['references'] if ref['role'] in roles]


def selection(root, project, request, film=None):
    try:
        binding = styles.load_binding(root, project)
        windows = _scenes(root, project, request, film, binding["overrides"])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise M2VError(f'评审缺少有效风格绑定或场景范围：{exc}') from exc
    rows = {}
    scope = {}
    uses = request.get('referenceUses', {})
    if not isinstance(uses, dict) or not uses.keys() <= windows.keys():
        raise M2VError('referenceUses 须按当前观察项 ID 登记参考条目')
    for item, scenes in windows.items():
        if not scenes and any(change['scope']['scenes'] != 'all' for change in binding['overrides']):
            raise M2VError('试制涉及逐场风格覆盖，请在请求 sceneIds 登记适用场景')
        scope[item] = {}
        requested = uses.get(item)
        if requested is not None and (not isinstance(requested, list)
                                      or any(not isinstance(k, str) for k in requested)
                                      or len(set(requested)) != len(requested)):
            raise M2VError('referenceUses 条目必须为不重复的 ID 列表')
        available = set()
        for scene in scenes or ['all']:
            keys = []
            for style, ref in _references(binding, scene):
                available.add(ref['id'])
                if requested is not None and ref['role'] != 'overall' and ref['id'] not in requested:
                    continue
                key = f"{style['id']}@{style['revision']}/{ref['id']}"
                row = {'role': ref['role'], 'scope': ref['scope'], 'evidence': ref['evidence'],
                       'snapshot': style.get('snapshot', {}).get(ref['id'])}
                if key in rows and rows[key] != row:
                    raise M2VError('相同参考修订指向不同内容')
                rows[key] = row
                if key not in keys:
                    keys.append(key)
            scope[item][scene] = keys
        if requested is not None and not set(requested) <= available:
            raise M2VError('referenceUses 引用了当前范围外的参考')
    return {'bindingDigest': dependencies.digest(local(root, styles.BINDING)),
            'referenceDigest': binding['referenceDigest'], 'items': scope, 'references': rows}


def _obtain(root, row):
    ev = row['evidence']
    digest = ev['sha256']
    if row['snapshot']:
        return styles.local_path(root, row['snapshot']['path'])
    # 本地副本须与登记原件逐字节一致。仅对照包取证允许访问外站。
    cache = local(root, f'outputs/style-evidence/{digest}', exists=False)
    for candidate in (cache, REPOSITORY_ROOT/'refs/type-default-style'/digest):
        if candidate.is_file() and dependencies.digest(candidate) == digest:
            return candidate
    cache.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache.parent) as directory:
        path = Path(directory)/'evidence'
        SafeHTTP().download(ev['url'], path)
        if styles.sha256(path) != digest:
            raise M2VError('远端证据与发布摘要不符')
        path.replace(cache)
    return cache


def _extension(path):
    with path.open('rb') as stream:
        header = stream.read(16)
    if header.startswith(b'\x89PNG'):
        return '.png'
    if header.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if header[4:8] == b'ftyp':
        return '.mp4'
    if header.startswith(b'\x1aE\xdf\xa3'):
        return '.webm'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return '.webp'
    if header[:4] == b'%PDF':
        return '.pdf'
    return '.txt'  # 官方规范以只读原文交付，不执行网页。


def supply(root, target, selection, conditions):
    """每件原始证据只放一份。缺证与观察条件按项目保留以供导入核验。"""
    entries, resolved = {}, {}
    for key, row in selection['references'].items():
        ev = row['evidence']
        entry = {'role': row['role'], 'scope': row['scope'], 'locator': ev['locator'], 'sha256': ev['sha256']}
        if ev['sha256'] not in resolved:
            try:
                path = _obtain(root, row)
                dest = target/f'style-{len(resolved):03d}{_extension(path)}'
                shutil.copyfile(path, dest)
                if styles.sha256(dest) != ev['sha256']:
                    dest.unlink()
                    raise M2VError('复制期间证据摘要发生变化')
                resolved[ev['sha256']] = {'file': dest.name}
            except (M2VError, OSError, ValueError) as exc:
                resolved[ev['sha256']] = {'missing': str(exc)}
        evidence = resolved[ev['sha256']]
        if (row['role'] == 'overall' and 'file' in evidence
                and Path(evidence['file']).suffix not in {'.png', '.jpg', '.webp', '.mp4', '.webm'}):
            evidence = {'missing': '整体标杆缺少可观察的实际视觉媒体'}
        entries[key] = {**entry, **evidence}
    index = {'references': entries, 'items': selection['items'], 'conditionsAvailable': bool(conditions)}
    write(target/'style-references.json', index)


def verify_coverage(index, report, inputs, pack):
    targets = {row["path"] for row in pack["files"] if row["path"].startswith("target-")}
    for item in report['coverage']:
        if item['status'] == 'insufficient':
            continue
        refs = {key for keys in index['items'][item['id']].values() for key in keys}
        needed = {index['references'][key].get('file') for key in refs}
        if (not refs or not index['conditionsAvailable'] or None in needed
                or not (needed | targets | {'style-references.json', 'conditions.json'}) <= inputs):
            raise M2VError('风格对照缺少当前窗口的实际参考、观察条件或读取证据，应记录 insufficient')
