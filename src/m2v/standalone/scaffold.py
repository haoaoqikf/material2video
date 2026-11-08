"""初始化时复制实际运行材料；不建立跨工程链接或运行时模板依赖。"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.core import security
from m2v.type_system.catalog import catalog


def template_files() -> list[Path]:
    """剪枝依赖、媒体、缓存后枚举模板，不能把开发机状态装进新作品。"""
    source = REPOSITORY_ROOT / 'templates/standalone'
    excluded = {'.git', '.venv', 'node_modules', '.cache', 'outputs', 'dist', '__pycache__'}
    files = []
    for directory, children, names in os.walk(source):
        folder = Path(directory)
        for name in children:
            path = folder / name
            if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
                raise M2VError(f'模板含越界目录链接：{path}')
        children[:] = [name for name in children if name not in excluded
                       and not name.endswith('.egg-info')
                       and (folder / name).relative_to(source).as_posix() not in
                       {'fonts/files', 'public/fonts', 'src/assets/math', 'assets/media', 'assets/sound'}]
        for name in names:
            path = folder / name
            if name.endswith(('.pyc', '.pyo', '.tsbuildinfo', '.log')):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
                raise M2VError(f'模板含越界链接：{path}')
            files.append(path)
    if not files:
        raise M2VError(f'独立工程模板缺失：{source}')
    return sorted(files)


def create(directory: str | Path, video_type: str, *, output: dict | None = None) -> Path:
    entry = catalog().get(video_type)
    root = Path(directory).expanduser().resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise M2VError(f'作品目录已存在且非空，未覆盖：{root}')
    root.parent.mkdir(parents=True, exist_ok=True)
    source = REPOSITORY_ROOT / 'templates/standalone'
    files = template_files()
    with tempfile.TemporaryDirectory(prefix='.video-init-', dir=root.parent) as temporary:
        stage = Path(temporary) / 'project'
        stage.mkdir()
        adopted = {}
        for path in files:
            relative = path.relative_to(source)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            adopted[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = json.loads((stage / 'project.json').read_text(encoding='utf-8'))
        slug = re.sub(r'[^a-z0-9-]+', '-', root.name.lower()).strip('-') or 'video'
        manifest.update(id=f'{slug[:50].rstrip("-")}-{uuid.uuid4().hex[:8]}', type=entry.name)
        manifest['output'].update(entry.initial_dimensions())
        manifest['output'].update(output or {})
        (stage / 'project.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        for material in entry.materials:
            target = stage / material.file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(material.template, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        # 这是生成时的来源记录；运行和指纹不再读取主项目模板。
        (stage / 'template-source.json').write_text(json.dumps({'version': 1, 'files': adopted},
                                                   ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        if root.exists():
            root.rmdir()  # 前面已核对为空；rmdir不会递归删除用户材料。
        security.deliver_directory(stage, root)
    return root / 'project.json'
