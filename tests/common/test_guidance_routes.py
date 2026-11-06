"""阅读路由与预算的可校验性：导航通过不等于实际理解或成片质量。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import guidance_docs
import sync_docs
from m2v.core.errors import M2VError

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / '.agents/skills/material2video'


def routes() -> dict:
    return json.loads((SKILL / 'references/guidance-routes.json').read_text(encoding='utf-8'))


def test_current_routes_and_budgets_pass():
    counts = guidance_docs.validate(ROOT)
    assert counts['entry'] <= 2000
    for stage in ('plan', 'iterate', 'final'):
        assert counts[stage] <= 3000
        assert counts['entry'] + counts[stage] <= 5000


def test_budget_excludes_frontmatter_and_generated_regions():
    body = guidance_docs.body('---\nname: x\n---\n\n开头\n<!-- generated:type-catalog:start -->\n很长\n'
                              '<!-- generated:type-catalog:end -->\n结尾\n')
    assert body == '开头\n\n结尾'


def test_anchors_ignore_template_fences():
    text = '# 示例\n\n```markdown\n## 视觉创意方案（七段式）\n```\n\n## 判断演练\n'
    found = guidance_docs.anchors(text)
    assert '判断演练' in found and '视觉创意方案七段式' not in found


def test_unclosed_template_cannot_hide_navigation():
    with pytest.raises(M2VError, match='未闭合代码围栏'):
        guidance_docs.validate_fences('```markdown\n## 模板\n\n## 实际导航\n', 'workflow.md')
    guidance_docs.validate_fences('```markdown\n## 模板\n```\n## 实际导航\n', 'workflow.md')


@pytest.mark.parametrize('mutation,match', [
    (lambda r: r['stages'][1].update(id='rough'), '三阶段'),
    (lambda r: r['stages'][1].update(id='refine'), '三阶段'),
    (lambda r: r['stages'].pop(), '三阶段'),
    (lambda r: r['stages'].append({'id': 'extra', 'guide': 'references/stage-final.md'}), '三阶段'),
    (lambda r: r['stages'][0].update(guide='references/stage-final.md'), '三阶段'),
    (lambda r: r['stages'][0].update(guide='references/missing.md'), '阅读目标不存在'),
    (lambda r: r['tasks'][0].update(guide='references/stage-plan.md#不存在的锚点'), '标题锚点不存在'),
    (lambda r: r['conditional'][0].update(when='  '), '触发条件'),
    (lambda r: r['types'].pop('data-evolution'), 'types'),
    (lambda r: r['ruleOwners'].pop('实际表达'), 'ruleOwners'),
    (lambda r: r.update(schemaVersion=2), '结构或版本无效'),
    (lambda r: r.update(entry='references/stage-plan.md'), 'SKILL.md'),
])
def test_invalid_routes_are_rejected(mutation, match):
    value = json.loads(json.dumps(routes()))
    mutation(value)
    with pytest.raises(M2VError, match=match):
        guidance_docs.validate(ROOT, value)


def _pad(monkeypatch, entry: int, stage: int) -> None:
    original = guidance_docs.body
    entry_path = SKILL / 'SKILL.md'
    stage_path = SKILL / routes()['stages'][0]['guide']
    entry_text, stage_text = entry_path.read_text(encoding='utf-8'), stage_path.read_text(encoding='utf-8')

    def body(text):
        if text == entry_text:
            return 'x' * entry
        if text == stage_text:
            return 'x' * stage
        return original(text)
    monkeypatch.setattr(guidance_docs, 'body', body)


@pytest.mark.parametrize('entry,stage,budget,match', [
    (1900, 3001, None, '阶段 3001/3000'),
    (2001, 100, None, '入口超预算'),
    # 入口 2000 加阶段 3000 恰好等于组合上限；用更小的组合上限验证它独立生效。
    (1900, 2200, 4000, '入口加阶段 4100/4000'),
])
def test_over_budget_is_rejected(entry, stage, budget, match, monkeypatch):
    if budget is not None:
        monkeypatch.setattr(guidance_docs, 'COMBINED_BUDGET', budget)
    _pad(monkeypatch, entry, stage)
    with pytest.raises(M2VError, match=match):
        guidance_docs.validate(ROOT)


def test_navigation_is_not_part_of_the_prepared_fingerprint():
    """阅读路由属于指导文档，不进入作品材料，因此不参与视频准备指纹。"""
    from m2v.type_system import catalog
    for entry in catalog.catalog().entries():
        materials = entry.material_map()
        assert not any('guidance' in value or 'stage-' in value for value in materials.values())


def test_doc_check_integrates_navigation_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(guidance_docs, 'validate', lambda root: calls.append(root) or {'entry': 1})
    assert sync_docs.main(['--check']) == 0
    assert calls
