"""独立的场景设计对应检查；不参与渲染或创意/审美判定。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / 'src'))

from guidance_docs import link_target, validate_fences
from m2v.core.errors import M2VError
from m2v.core.project import load_project

ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
LINK = re.compile(r'\[([^\]\n]*)\]\(([^)\n]+)\)')
RESERVED = {'con', 'prn', 'aux', 'nul'} | {f'{prefix}{n}' for prefix in ('com', 'lpt') for n in range(1, 10)}


def plain(text: str, name: str) -> str:
    """复用围栏合法性规则，模板中的占位链接不作为活动索引。"""
    validate_fences(text, name)
    result, marker = [], None
    for line in text.splitlines():
        match = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if match:
            token, suffix = match.groups()
            if marker is None:
                marker = token
            elif token[0] == marker[0] and len(token) >= len(marker) and not suffix.strip():
                marker = None
            continue
        if marker is None:
            result.append(line)
    return '\n'.join(result)


def _document(path: Path) -> str:
    try:
        value = plain(path.read_text(encoding='utf-8'), path.name)
    except OSError as exc:
        raise M2VError(f'设计文档不存在或不可读：{path}') from exc
    if not re.sub(r'[#\s]', '', value):
        raise M2VError(f'设计文档内容为空：{path}')
    # 该轻量工具不实现第二套 Markdown 解析器；未支持的引用语法须显式失败，
    # 防止把未检查的证据链接误报为有效。普通正文和任务复选框不受影响。
    if re.search(r'\[[^\]\n]+\]\s*\[[^\]\n]*\]|^\s{0,3}\[[^\]\n]+\]:', value, re.M):
        raise M2VError(f'设计检查仅支持内联链接，请展开引用式链接：{path}')
    if re.search(r'<[^>]+\b(?:href|src)\s*=', value, re.I):
        raise M2VError(f'设计检查仅支持内联链接，请展开 HTML 链接或图片：{path}')
    return value


def _local(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise M2VError(f'场景设计路径越界：{path}')
    return resolved


def _links(root: Path, path: Path, content: str, selected: set[str] | None = None,
           known: set[str] | None = None) -> None:
    deferred = {root / 'design/scenes' / f'{sid}.md' for sid in (known or set()) - (selected or set())} if selected is not None else set()
    for label, reference in LINK.findall(content):
        ref = reference.strip()
        if urlsplit(ref).scheme in {'http', 'https', 'mailto'}:
            continue
        if urlsplit(ref).scheme:
            raise M2VError(f'设计文档链接协议无效：{ref}')
        raw = unquote(ref).partition('#')[0]
        candidate = (path.parent / raw).resolve() if raw else path.resolve()
        # 只有规范化后恰为已知未选场景的链接可暂缓；先判路径，避免 ../ 或未知ID绕过。
        if candidate in deferred:
            continue
        scope = REPO_ROOT if candidate.is_relative_to(REPO_ROOT) else root
        link_target(scope, path if not raw else path.parent, ref)


def validate(root: Path, scene_ids: list[str] | None = None) -> dict:
    root, project = load_project(root)
    try:
        board = json.loads((root / project['materials']['storyboard']).read_text(encoding='utf-8'))
        ids = [row['id'] for row in board['scenes']]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise M2VError(f'无法读取分镜场景：{exc}') from exc
    if (not ids or any(not isinstance(i, str) or not ID.fullmatch(i) or i.casefold() in RESERVED for i in ids)
            or len(ids) != len({i.casefold() for i in ids})):
        raise M2VError('分镜 scene.id 为空、重复或不能作为场景文档文件名')
    selected = set(ids if scene_ids is None else scene_ids)
    if not selected or not selected <= set(ids):
        raise M2VError(f'未知或空场景选择：{sorted(selected - set(ids))}')
    design = _local(root, root / 'DESIGN.md')
    research = _local(root, root / 'RESEARCH.md')
    _links(root, research, _document(research))
    content = _document(design)
    indexed: dict[str, int] = {}
    for label, ref in LINK.findall(content):
        raw = unquote(ref.strip()).partition('#')[0]
        # 章节深链用于引用细节，不是第二条场景索引。
        if '#' in ref and label not in ids:
            continue
        if not raw.startswith('design/scenes/') and label not in selected:
            continue
        if scene_ids is not None and label not in selected:
            continue
        path = _local(root, root / raw)
        expected = root / 'design/scenes' / f'{label}.md'
        if label not in ids or path != expected or raw != f'design/scenes/{label}.md':
            raise M2VError(f'场景索引错配：[{label}]({ref})')
        indexed[label] = indexed.get(label, 0) + 1
    for scene_id in selected:
        if indexed.get(scene_id) != 1:
            raise M2VError(f'场景索引缺失或重复：{scene_id}')
    if any(count != 1 for count in indexed.values()):
        raise M2VError('场景索引重复')
    folder = _local(root, root / 'design/scenes')
    if scene_ids is None:
        extra = {p.stem for p in folder.glob('*.md')} - set(ids)
        if extra:
            raise M2VError(f'存在不属于当前分镜的场景文档：{sorted(extra)}')
    partial = selected if scene_ids is not None else None
    _links(root, design, content, partial, set(ids))
    for scene_id in sorted(selected):
        path = _local(root, folder / f'{scene_id}.md')
        _links(root, path, _document(path), partial, set(ids))
    return {'scenes': sorted(selected), 'scope': 'partial' if scene_ids is not None else 'complete',
            'meaning': '仅结构对应通过，不代表设计内容、实际效果或独立评审通过'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--scene', action='append', help='只检查指定场景；可重复')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate(args.project, args.scene), ensure_ascii=False))
    except (M2VError, OSError, ValueError) as exc:
        print(f'[error] {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
