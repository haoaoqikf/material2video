"""一次查询内复用读取与摘要；按可达依赖绑定，动态引用保守扩大。"""
from __future__ import annotations

import json
import os
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


def owned_files(root: Path, folder: Path):
    """遍历前检查目录联接，不能枚举作品外的依赖或字体。"""
    if not folder.resolve().is_relative_to(root):
        raise M2VError('场景资源或字体链接越过作品目录')
    for directory, children, names in os.walk(folder, followlinks=False):
        parent = Path(directory)
        for path in [parent, *(parent / name for name in children)]:
            if not path.resolve().is_relative_to(root):
                raise M2VError('场景资源或字体链接越过作品目录')
        for name in names:
            path = (parent / name).resolve()
            if not path.is_relative_to(root):
                raise M2VError('场景资源或字体链接越过作品目录')
            if path.is_file():
                yield path


def scene_sources(root: Path, scene: dict) -> dict:
    from m2v.core.source_imports import import_specifiers, resolve_import
    root = root.resolve()
    cache = _snapshot.get()
    key = (root, fingerprint(scene))
    if cache is not None and key in cache['scenes']:
        return cache['scenes'][key]
    paths, bodies, warnings = set(), [], []
    queue = [local(root, scene['content']['entry'])]
    # 受控时钟、宿主和字体由作品自己的构建注入，也是真实的画面输入。
    queue += [root / name for name in ('src/code-scene/host.tsx', 'src/code-scene/capture-clock.js',
                                      'src/fonts.ts', 'src/frames.ts') if (root / name).is_file()]
    while queue:
        path = queue.pop().resolve()
        if path in paths:
            continue
        if not path.is_relative_to(root):
            raise M2VError('场景依赖越过作品目录')
        paths.add(path)
        if path.suffix.lower() not in ('.tsx', '.ts', '.jsx', '.js', '.css', '.mjs', '.cjs', '.json'):
            continue
        body = text(path)
        bodies.append(body)
        for specifier in import_specifiers(body):
            if specifier.startswith('m2v/'):
                raise M2VError(f'主项目运行时引用已移除：{specifier}；请采用作品内组件')
            target = resolve_import(specifier, path, root)
            if target:
                queue.append(target)
            elif specifier.startswith(('.', '/', '@/', '~/')):
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
    for folder in (root / 'fonts/files',):
        if folder.exists():
            paths.update(owned_files(root, folder))
    for name in ('src/video-config.json', 'fonts/registry.json', 'package.json', 'pnpm-lock.yaml',
                 'pyproject.toml', 'uv.lock', 'asset-loaders.json', 'scripts/build-code-scene.mjs',
                 'scripts/scene-inputs.mjs', 'scripts/sync-fonts.mjs'):
        path = root / name
        if path.is_file():
            paths.add(path)
    if warnings:
        for name in ('scenes', 'components', 'src', 'assets', 'fonts/files'):
            paths.update(owned_files(root, root / name))
    paths = {p.resolve() for p in paths}
    if any(not p.is_relative_to(root) for p in paths):
        raise M2VError('场景资源或字体链接越过作品目录')
    result = {'files': {'work/' + p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)},
              'assetRecords': selected_assets, 'conservativeReasons': sorted(set(warnings))}
    if cache is not None:
        cache['scenes'][key] = result
    return result
