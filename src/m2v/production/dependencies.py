"""一次查询内复用读取与摘要；按可达依赖绑定，动态引用保守扩大。"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from m2v.core.delivery import digest as file_digest
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from .storage import local

_snapshot = ContextVar('production_dependency_snapshot', default=None)


@contextmanager
def snapshot():
    # 不能跨查询缓存：外部编辑必须在下一次只读查询立即可见。
    if _snapshot.get() is not None:
        yield
        return
    token = _snapshot.set({'digests': {}, 'text': {}, 'scenes': {}})
    try:
        yield
    finally:
        _snapshot.reset(token)


def digest(path: Path) -> str:
    cache = _snapshot.get()
    if cache is None:
        return file_digest(path)
    key = path.resolve()
    if key not in cache['digests']:
        cache['digests'][key] = file_digest(path)
    return cache['digests'][key]


def text(path: Path) -> str:
    cache = _snapshot.get()
    if cache is None:
        return path.read_text(encoding='utf-8')
    key = path.resolve()
    if key not in cache['text']:
        cache['text'][key] = path.read_text(encoding='utf-8')
    return cache['text'][key]


def scene_sources(root: Path, scene: dict) -> dict:
    from m2v.core.source_imports import import_specifiers, resolve_import
    from m2v.engine.contract_page import web_dir
    root = root.resolve()
    web = web_dir().resolve()
    cache = _snapshot.get()
    key = (root, fingerprint(scene))
    if cache is not None and key in cache['scenes']:
        return cache['scenes'][key]
    paths, bodies, warnings = set(), [], []
    math_used = False
    queue = [local(root, scene['content']['entry'])]
    while queue:
        path = queue.pop().resolve()
        if path in paths:
            continue
        if not path.is_relative_to(root) and not path.is_relative_to(web):
            raise M2VError('场景依赖越过作品和共享运行时根')
        paths.add(path)
        if path.suffix.lower() not in ('.tsx', '.ts', '.jsx', '.js', '.css', '.mjs', '.json'):
            continue
        body = text(path)
        bodies.append(body)
        for specifier in import_specifiers(body):
            if specifier == 'm2v/style' or specifier.startswith('m2v/style/'):
                raise M2VError(f'风格包入口已移除：{specifier}')
            if specifier.startswith('m2v/code-scene/'):
                registry = web / 'src/code-scene/entries.json'
                if registry.is_file():
                    paths.add(registry)
                math_used |= specifier == 'm2v/code-scene/math'
            target = resolve_import(specifier, path, web)
            if target:
                queue.append(target)
            elif specifier.startswith(('.', '/', '@/', 'm2v/code-scene/')):
                warnings.append('未解析本地引用，保守绑定作品素材与字体')
        if re.search(r'\bimport\s*\(\s*[^\s\'"]', body):
            warnings.append('动态导入，保守绑定作品源码、素材与字体')
    combined = '\n'.join(bodies) + json.dumps(scene.get('content', {}).get('props', {}), ensure_ascii=False)
    literal_ids = set(re.findall(r"\buseMediaAsset\(\s*['\"]([^'\"]+)['\"]\s*\)", combined))
    if len(re.findall(r'\buseMediaAsset\s*\(', combined)) > len(re.findall(
            r"\buseMediaAsset\(\s*['\"]([^'\"]+)['\"]\s*\)", combined)):
        warnings.append('动态素材 ID，保守绑定全部登记素材')
    record = root / 'assets/media-sources.json'
    selected_assets = []
    if record.exists():
        assets = json.loads(text(record)).get('assets', [])
        selected_assets = [a for a in assets if a['id'] in literal_ids or warnings]
        for asset in selected_assets:
            paths.add(local(root, asset['path']))
        missing = literal_ids - {a['id'] for a in assets}
        if missing:
            raise M2VError(f'场景引用未登记素材：{sorted(missing)}')
    elif literal_ids:
        raise M2VError('场景引用素材但缺少来源登记')
    # 字体及运行时由服务器注入，不一定以 import 出现，必须显式包含。
    for folder in (web / 'public/fonts', root / 'fonts'):
        if folder.exists():
            paths.update(p for p in folder.rglob('*') if p.is_file())
    for name in ('src/fonts.ts', 'src/frames.ts', 'src/video-config.json', 'package.json', 'pnpm-lock.yaml'):
        path = web / name
        if path.is_file():
            paths.add(path)
    if math_used:
        registry = web.parent / 'fonts/registry.json'
        if not registry.is_file():
            raise M2VError('公式字体登记缺失')
        paths.add(registry)
    if warnings:
        for name in ('scenes', 'assets', 'fonts'):
            paths.update(p for p in (root / name).rglob('*') if p.is_file())
    def label(path):
        if path.is_relative_to(root):
            return 'work/' + path.relative_to(root).as_posix()
        if path.is_relative_to(web):
            return 'web/' + path.relative_to(web).as_posix()
        return 'repo/' + path.relative_to(web.parent).as_posix()
    result = {'files': {label(p): digest(p) for p in sorted(paths)},
              'assetRecords': selected_assets, 'conservativeReasons': sorted(set(warnings))}
    if cache is not None:
        cache['scenes'][key] = result
    return result
