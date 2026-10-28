"""阅读导航和预算的离线检查；不猜测 AI 阅读或审美质量。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from m2v.core.errors import M2VError

SKILL = Path('.agents/skills/material2video')
STAGES = {'plan', 'iterate', 'final'}
TASKS = {'new', 'revision', 'review', 'diagnose'}
TYPES = {'general', 'financial-timeseries', 'housing-timeseries'}
OWNERS = {'事实许可', '字体确定性', '独立隔离', '证据完成', '失败回退', '讲解机制', '实际表达', '过程证据容量'}
#: 正文字符预算；入口加当前阶段同时受限，避免「各自达标但合读仍过长」。
ENTRY_BUDGET, STAGE_BUDGET, COMBINED_BUDGET = 2000, 3000, 5000


def body(text: str) -> str:
    text = text.replace('\r\n', '\n')
    text = re.sub(r'\A---\n.*?\n---\n', '', text, flags=re.S)
    return re.sub(r'<!-- generated:([\w-]+):start -->.*?<!-- generated:\1:end -->', '', text, flags=re.S).strip()


def anchors(text: str) -> set[str]:
    # 模板围栏里的伪标题不会成为 Markdown 标题锚点。
    plain = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.S | re.M)
    result, counts = set(), {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*$', plain, re.M):
        slug = re.sub(r'[^\w\-\s]', '', heading.lower().replace('`', '')).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug + (f'-{count}' if count else ''))
    result.update(re.findall(r'<a\s+id=["\']([^"\']+)["\']', plain))
    return result


def target(root: Path, base: Path, reference: str) -> Path:
    if not isinstance(reference, str) or not reference.strip():
        raise M2VError('阅读路由目标必须是非空文字')
    raw, _, anchor = unquote(reference).partition('#')
    path = (base / raw).resolve() if raw else base.resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise M2VError(f'阅读目标不存在或越界：{reference}')
    if anchor and anchor not in anchors(path.read_text(encoding='utf-8')):
        raise M2VError(f'阅读目标标题锚点不存在：{reference}')
    return path


def _rows(value, keys: set[str], name: str) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise M2VError(f'{name} 必须为非空列表')
    if any(not isinstance(row, dict) or set(row) != keys for row in value):
        raise M2VError(f'{name} 字段无效，应为 {sorted(keys)}')
    ids = [row['id'] for row in value]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise M2VError(f'{name} ID 为空或重复')
    return value


def validate(root: Path, routes: dict | None = None) -> dict[str, int]:
    base = root / SKILL
    try:
        if routes is None:
            routes = json.loads((base / 'references/guidance-routes.json').read_text(encoding='utf-8'))
        required = {'schemaVersion', 'entry', 'stages', 'tasks', 'types', 'conditional', 'ruleOwners'}
        if not isinstance(routes, dict) or set(routes) != required or type(routes['schemaVersion']) is not int or routes['schemaVersion'] != 1:
            raise M2VError('阅读路由清单结构或版本无效')
        if routes['entry'] != 'SKILL.md':
            raise M2VError('阅读入口必须是 SKILL.md')
        stages = _rows(routes['stages'], {'id', 'guide'}, 'stages')
        tasks = _rows(routes['tasks'], {'id', 'guide', 'when'}, 'tasks')
        conditional = _rows(routes['conditional'], {'id', 'guide', 'when'}, 'conditional')
        if {r['id'] for r in stages} != STAGES or len({r['guide'] for r in stages}) != len(STAGES):
            raise M2VError('三阶段必须各有唯一主指南')
        if {r['id'] for r in tasks} != TASKS:
            raise M2VError('任务路由必须覆盖 new/revision/review/diagnose')
        for name, keys in (('types', TYPES), ('ruleOwners', OWNERS)):
            if not isinstance(routes[name], dict) or set(routes[name]) != keys:
                raise M2VError(f'{name} 缺少类型或规则归属')
        for row in tasks + conditional:
            if not isinstance(row['when'], str) or not row['when'].strip():
                raise M2VError(f'{row["id"]} 缺少触发条件')
        entry = target(root, base, routes['entry'])
        paths = {entry}
        for reference in [r['guide'] for r in stages + tasks + conditional] + list(routes['types'].values()) + list(routes['ruleOwners'].values()):
            paths.add(target(root, base, reference))
        counts = {'entry': len(body(entry.read_text(encoding='utf-8')))}
        if counts['entry'] > ENTRY_BUDGET:
            raise M2VError(f'Skill 入口超预算：{counts["entry"]} > {ENTRY_BUDGET}')
        for row in stages:
            path = target(root, base, row['guide'])
            count = len(body(path.read_text(encoding='utf-8')))
            counts[row['id']] = count
            if count > STAGE_BUDGET:
                raise M2VError(f'{row["id"]} 超预算：阶段 {count}/{STAGE_BUDGET}')
            if count + counts['entry'] > COMBINED_BUDGET:
                raise M2VError(f'{row["id"]} 超预算：入口加阶段 {count + counts["entry"]}/{COMBINED_BUDGET}')
        # 所有路由目标文档的相对链接和 JSON 示例必须可用。
        for path in paths:
            if path.suffix != '.md':
                continue
            text = path.read_text(encoding='utf-8')
            # 模板围栏里的占位链接是填写示例，不是活动文档引用。
            plain = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.S | re.M)
            for reference in re.findall(r'\]\(([^)\n]+)\)', plain):
                if '://' not in reference and not reference.startswith('mailto:'):
                    target(root, path.parent if not reference.startswith('#') else path, reference)
            for block in re.findall(r'```json\s*\n(.*?)\n```', text, re.S):
                try:
                    json.loads(block)
                except ValueError as exc:
                    raise M2VError(f'{path.name} JSON 示例无效：{exc}') from exc
        return counts
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise M2VError(f'阅读路由无法校验：{exc}') from exc
