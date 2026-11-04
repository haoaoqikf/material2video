"""唯一问题表中的机器块；不复制问题现象到状态数据库。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from .contract import fields, text
from .workflow import GATE_IDS
from .storage import atomic_text, local

BLOCK = re.compile(r'^```m2v-issues\s*\n(.*?)^```\s*$', re.M | re.S)
CAUSES = frozenset({'implementation', 'design', 'mixed', 'undetermined'})


def load(root: Path, *, required=False, _reopening_id=None, _review_context=None) -> list[dict]:
    path = outputs(root) / 'visual-notes.md'
    if not path.exists():
        if required:
            raise M2VError('缺少唯一问题表，不能推断没有保护引用')
        return []
    source = path.read_text(encoding='utf-8')
    matches = BLOCK.findall(source)
    if not matches and not required:
        return []
    if len(matches) != 1:
        raise M2VError('唯一问题表必须含一个 m2v-issues JSON 块')
    try:
        items = json.loads(matches[0])
    except ValueError as exc:
        raise M2VError('唯一问题表机器块损坏') from exc
    validate(root, items, _reopening_id=_reopening_id, _review_context=_review_context)
    return items


def validate(root: Path, items, *, _reopening_id=None, _review_context=None) -> None:
    if not isinstance(items, list):
        raise M2VError('问题机器块必须为列表')
    seen = set()
    for item in items:
        fields(item, {'id', 'status', 'required', 'gate', 'sceneId', 'checkpointId', 'caughtAt', 'catchableAt',
                      'evidence', 'versionRefs'}, {'uncatchableReason', 'cause'})
        if 'cause' in item and (not isinstance(item['cause'], str) or item['cause'] not in CAUSES):
            raise M2VError('问题 cause 必须为 implementation/design/mixed/undetermined')
        if item['status'] == 'closed' and item.get('cause') == 'undetermined':
            raise M2VError('问题关闭前必须定位设计或实现原因')
        if text(item['id']) in seen or item['status'] not in ('open', 'closed') or type(item['required']) is not bool:
            raise M2VError('问题 ID 重复、状态或必改标识无效')
        seen.add(item['id'])
        for key in ('gate', 'caughtAt', 'catchableAt'):
            if item[key] not in GATE_IDS:
                raise M2VError(f'问题 {key} 无效')
        if not isinstance(item['versionRefs'], list) or not isinstance(item['evidence'], list):
            raise M2VError('问题证据与版本引用必须为列表')
        if item['id'].startswith('REVIEW-') and not item['required']:
            raise M2VError('独立评审必改项不能降级为非必改')
        # 显式重开允许替换本项已过期的闭环证据；只读查询仍严格核验。
        if item['status'] == 'closed' and item['id'] != _reopening_id:
            if not item['evidence']:
                raise M2VError('关闭问题必须有复查证据')
            for entry in item['evidence']:
                fields(entry, {'path', 'sha256', 'gate'})
                from m2v.core.delivery import digest
                if digest(local(outputs(root), entry['path'])) != entry['sha256']:
                    raise M2VError('问题复查证据摘要不匹配')
            if item['catchableAt'] < item['caughtAt'] and not item.get('uncatchableReason'):
                if not any(e['gate'] == item['catchableAt'] for e in item['evidence']):
                    raise M2VError('迟到缺陷必须附最早可拦截门的回归证据')
            if item['id'].startswith('REVIEW-'):
                if _review_context is None:
                    from . import contract, ledger
                    events, diagnostics = ledger.history(root)
                    _review_context = (events, contract.load(root), diagnostics)
                _require_independent_recheck(root, item, _review_context)


def _require_independent_recheck(root: Path, item: dict, context: tuple) -> None:
    """仅接受实际已导入、同范围且未过期的独立复查，不相信说明文件。"""
    from . import acceptance, ledger, policy
    events, c, diagnostics = context
    if diagnostics:
        raise M2VError('制作历史损坏，不能关闭独立评审问题')
    failed = [e for e in events if e['type'] == 'review' and e['data'].get('verdict') == 'fail'
              and 'REVIEW-' + e['data'].get('roundId', '') + '-' + e['data'].get('reviewerId', '') == item['id']]
    if not failed:
        raise M2VError('找不到独立评审问题的原始失败记录')
    original = failed[-1]
    scope = {x['checkpointId'] for x in original['data'].get('coverage', [])}
    for event in events:
        data = event['data']
        if (event['type'] != 'review' or data.get('verdict') != 'pass'
                or data.get('isolation') != 'independent-subagent'
                or data.get('reviewType') != original['data'].get('reviewType')
                or event['gate'] != item['gate'] or event['time'] <= original['time']
                or (item['sceneId'] and event['sceneId'] not in (None, item['sceneId']))):
            continue
        coverage = data.get('coverage', [])
        if not scope or not scope <= {x['checkpointId'] for x in coverage if x.get('status') == 'pass'}:
            continue
        if data.get('round') == 'core' and data.get('reviewType') == 'blind' and not acceptance.core_coverage_passed(
                coverage, scope & policy.core_checkpoint_ids(c)):
            continue
        try:
            current = ledger.event_upstream(root, c, event)
        except (M2VError, OSError, ValueError, TypeError, KeyError):
            # 历史复查可能引用已删除或过期的采集；继续查找较新的有效复查。
            continue
        if event['upstream'] != current:
            continue
        if not ledger.evidence_valid(root, event['evidence']):
            continue
        # 闭环材料必须直接引用导入的报告，不能仅引用评审包或量测文件。
        report_digest = data.get('reportId')
        if any(entry['sha256'] == report_digest and entry['gate'] == event['gate']
               and any(e['path'] == entry['path'] and e['sha256'] == report_digest for e in event['evidence'])
               for entry in item['evidence']):
            return
    raise M2VError('关闭独立评审问题须引用同范围、当前有效的独立通过复查报告')


def update(root: Path, item: dict) -> None:
    path = outputs(root) / 'visual-notes.md'
    source = path.read_text(encoding='utf-8') if path.exists() else '# 制作问题与复查\n'
    items = load(root, _reopening_id=item['id'] if item.get('status') == 'open' else None)
    previous = next((x for x in items if x['id'] == item['id']), None)
    if previous and 'cause' in previous and 'cause' not in item:
        raise M2VError('已登记的问题归因不能删除，关闭前须完成定位')
    if previous and item['id'].startswith('REVIEW-') and any(
            item.get(key) != previous[key] for key in ('required', 'gate', 'sceneId', 'checkpointId', 'caughtAt', 'catchableAt')):
        raise M2VError('独立评审问题不能改变原范围或必改性质')
    items = [x for x in items if x['id'] != item['id']] + [item]
    validate(root, items)
    block = '```m2v-issues\n' + json.dumps(items, ensure_ascii=False, indent=2) + '\n```'
    source = BLOCK.sub(lambda _: block, source) if BLOCK.search(source) else source.rstrip() + '\n\n' + block + '\n'
    atomic_text(path, source)
