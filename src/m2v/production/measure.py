"""作者标记元素的可见状态与布局量测；未知覆盖不等于通过。"""
from __future__ import annotations

DOM = r"""() => {
 const nodes = [...document.querySelectorAll('[data-m2v-role]')];
 return nodes.map((el, index) => {
   const r = el.getBoundingClientRect(), s = getComputedStyle(el);
   let visible = r.width > 0 && r.height > 0, clipped = false;
   for (let n = el; n; n = n.parentElement) {
     const st = getComputedStyle(n), box = n.getBoundingClientRect();
     if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) visible = false;
     if (n !== el && /(hidden|clip|scroll|auto)/.test(st.overflow + st.overflowX + st.overflowY))
       clipped ||= r.left < box.left || r.top < box.top || r.right > box.right || r.bottom > box.bottom;
   }
   return {id:el.id || `element-${index}`, role:el.dataset.m2vRole, state:el.dataset.m2vState || '',
     color:s.fill !== 'none' ? s.fill : s.color, visible, clipped, text:el.textContent?.trim() || '',
     fontSize:parseFloat(s.fontSize), lineHeight:parseFloat(s.lineHeight),
     scrollWidth:el.scrollWidth, clientWidth:el.clientWidth,
     x:r.x, y:r.y, width:r.width, height:r.height,
     parents:nodes.filter(p => p !== el && p.contains(el)).map(p => p.id || `element-${nodes.indexOf(p)}`)};
 });
}"""


def expected_at(cp: dict, frame: int) -> list[dict]:
    planned = [item for plan in cp.get('statePlan', []) if plan['window'][0] <= frame < plan['window'][1]
               for item in plan['expected']]
    # 时间窗状态优先于单帧默认值，允许过程中的数量与结果不同。
    roles = {item['role'] for item in planned}
    return [item for item in cp['expected'] if frame == cp['frame'] and item['role'] not in roles] + planned


def evaluate(elements: list[dict], cp: dict, *, width: int, height: int, frame: int,
             safe_area: dict | None = None) -> list[dict]:
    checks = []

    def result(name, state, detail):
        checks.append({'name': name, 'status': state, 'detail': detail})

    visible = {e['id']: e for e in elements if e['visible']}
    values = list(visible.values())
    for expected in expected_at(cp, frame):
        pool = values if expected.get('visible', True) else [e for e in elements if not e['visible']]
        matches = [e for e in pool if e['role'] == expected['role'] and
                   ('state' not in expected or e['state'] == expected['state']) and
                   ('color' not in expected or e['color'].lower() == expected['color'].lower())]
        state = 'pass' if abs(len(matches) - expected['count']) <= expected.get('tolerance', 0) else 'fail'
        if not elements:
            state = 'unverified'
        result('对象状态:' + expected['role'], state,
               {'expected': expected['count'], 'actual': len(matches), 'occlusion': 'DOM 不证明像素遮挡'})
    rules = cp.get('measurement', {})
    allowed = {frozenset(pair) for pair in rules.get('allowedOverlaps', [])}
    for e in values:
        if e['x'] < 0 or e['y'] < 0 or e['x'] + e['width'] > width + .5 or e['y'] + e['height'] > height + .5 or e['clipped']:
            result('裁切:' + e['id'], 'fail', e)
        if e['role'] in rules.get('bodyRoles', []):
            size = e['fontSize'] * 393 / width
            minimum = rules.get('minFont393')
            source = rules.get('thresholdSource')
            result('字号:' + e['id'], 'unverified' if minimum is None or not source else 'pass' if size >= minimum else 'fail',
                   {'font393': size, 'minimum': minimum, 'source': source})
            safe = rules.get('subtitleTop')
            if safe is not None and e['y'] + e['height'] > safe:
                result('字幕安全区:' + e['id'], 'fail', {'subtitleTop': safe})
    # 作品自绘的屏幕字幕：共享字幕层在无旁白时为空，必须单独检查安全区与单行。
    for role in rules.get('subtitleRoles', []):
        for e in [item for item in values if item['role'] == role]:
            if safe_area is not None:
                inside = (e['x'] >= safe_area['x'] - .5 and e['y'] >= safe_area['y'] - .5
                          and e['x'] + e['width'] <= safe_area['x'] + safe_area['width'] + .5
                          and e['y'] + e['height'] <= safe_area['y'] + safe_area['height'] + .5)
                result('屏幕字幕安全区:' + e['id'], 'pass' if inside else 'fail',
                       {'safeArea': safe_area, 'box': {k: e[k] for k in ('x', 'y', 'width', 'height')}})
            overflow = e.get('scrollWidth', 0) > e.get('clientWidth', e['width']) + 1
            multiline = '\n' in e['text'] or (e.get('lineHeight') and e['height'] > e['lineHeight'] * 1.5)
            result('屏幕字幕单行:' + e['id'], 'fail' if overflow or multiline else 'pass',
                   {'overflow': overflow, 'multiline': multiline, 'text': e['text']})
    for i, a in enumerate(values):
        for b in values[i + 1:]:
            if a['id'] in b['parents'] or b['id'] in a['parents'] or frozenset((a['role'], b['role'])) in allowed:
                continue
            if min(a['x'] + a['width'], b['x'] + b['width']) > max(a['x'], b['x']) and min(a['y'] + a['height'], b['y'] + b['height']) > max(a['y'], b['y']):
                result('未授权重叠', 'fail', [a['id'], b['id']])
    for role in dict.fromkeys(plan['role'] for plan in cp['textPlan']):
        matches = [e for e in values if e['role'] == role]
        active = [plan['text'] for plan in cp['textPlan'] if plan['role'] == role and
                  plan['window'][0] <= frame < plan['window'][1]]
        valid = all(any(e['text'] == text for e in matches) for text in active) if active else not matches
        result('文字状态:' + role, 'pass' if valid else 'fail', {'visible': bool(active), 'text': active})
    for word in cp['forbidden']:
        result('禁止项:' + word, 'fail' if any(word in e['text'] for e in values) else 'pass', word)
    if not elements:
        result('观测范围', 'unverified', '没有作者 DOM 标记；Canvas/WebGL 需要探针或人工逐项证据')
    if not rules.get('thresholdSource'):
        result('文字预算', 'unverified', '缺少文字计划量测规则及阈值来源')
    elif rules.get('maxTextCharacters') is not None:
        total = sum(len(e['text']) for e in values if e['role'] in rules.get('bodyRoles', []))
        result('文字预算', 'pass' if total <= rules['maxTextCharacters'] else 'fail', {'characters': total, 'limit': rules['maxTextCharacters']})
    return checks


def evaluate_probe(probe: list[dict], cp: dict, *, frame: int | None = None) -> list[dict]:
    checks = []
    for expected in expected_at(cp, cp['frame'] if frame is None else frame):
        matches = [item for item in probe if item.get('role') == expected['role'] and
                   ('state' not in expected or item.get('state') == expected['state'])]
        actual = matches[0] if len(matches) == 1 else None
        valid = actual is not None and all(actual.get(key) == value for key, value in expected.items()
                                           if key not in ('tolerance',))
        checks.append({'name': '可选状态探针:' + expected['role'], 'status': 'pass' if valid else 'fail',
                       'detail': {'expected': expected, 'actual': actual, 'coverage': '作者导出状态，不证明像素遮挡'}})
    return checks
