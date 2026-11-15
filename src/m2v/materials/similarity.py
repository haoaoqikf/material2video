"""只读相似镜头建议；模型空间分桶、分块比较、代表约束，不执行合并或删除。"""
from __future__ import annotations

import math

import numpy as np

from .contracts import fingerprint
from .errors import MaterialError
from .indexing import load_vectors


def similar(store, *, threshold=.96, max_items=1000):
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise MaterialError('invalid-request', '相似度须为 (0,1] 的有限数值', stage='library')
    if type(max_items) is not int or not 2 <= max_items <= 5000:
        raise MaterialError('invalid-request', '相似条目预算须为 2..5000', stage='library')
    latest = {}
    for index in store.documents('material.index'):
        if index.data.channel != 'visual' or index.data.status != 'complete' or index.data.embeddingSpec is None:
            continue
        key = index.data.mediaId
        if key not in latest or (index.createdAt, index.id) > (latest[key].createdAt, latest[key].id):
            latest[key] = index
    spaces, excluded, count, truncated = {}, [], 0, False
    for media_id, index in sorted(latest.items()):
        if count >= max_items:
            truncated = True
            break
        try:
            media = store.get(media_id, kind='material.media')
            if (index.data.mediaSha256 != media.data.artifact.sha256 or
                    index.data.timelineMappingSha256 != fingerprint(media.data.probe.timeline)):
                raise MaterialError('conflict', '视觉索引已过期', stage='library')
            store.verify_artifact(media.data.artifact)
            matrix = load_vectors(store, index)
            records = store.records(index.id)
            spec = index.data.embeddingSpec
            space = fingerprint(spec.model_dump(mode='json'))
            vectors, items = [], []
            for record in records:
                if count + len(items) >= max_items:
                    truncated = True
                    break
                if record.vectorRow is None or record.frame is None:
                    continue
                store.verify_artifact(record.frame)
                vector = matrix[record.vectorRow]
                norm = float(np.linalg.norm(vector))
                if not math.isfinite(norm) or norm <= 0:
                    raise MaterialError('hash-mismatch', '视觉向量不可归一化', stage='library')
                vectors.append(vector / norm)
                items.append({'mediaId': media_id, 'sourceId': media.data.sourceId,
                    'indexId': index.id, 'recordId': record.id,
                    'localRange': record.localRange.model_dump(mode='json') if record.localRange else None,
                    'frame': record.frame.model_dump(mode='json')})
            if items:
                bucket = spaces.setdefault(space, {'spec': spec.model_dump(mode='json'), 'vectors': [], 'items': []})
                bucket['vectors'].extend(vectors)
                bucket['items'].extend(items)
                count += len(items)
        except (MaterialError, OSError, IndexError) as exc:
            if len(excluded) < 1000:
                excluded.append({'mediaId': media_id, 'reason': getattr(exc, 'code', 'invalid-index')})
    groups = []
    for space, bucket in sorted(spaces.items()):
        if len(bucket['items']) < 2:
            continue
        matrix = np.ascontiguousarray(bucket['vectors'], dtype='float32')
        assigned = set()
        # 峰值比较矩阵最多 64×N，而不是 N×N；每个组直接与代表比较，避免传递误合并。
        for start in range(0, len(matrix), 64):
            scores = matrix[start:start + 64] @ matrix.T
            for local, row in enumerate(scores):
                representative = start + local
                if representative in assigned:
                    continue
                members = [j for j in range(representative + 1, len(matrix))
                           if j not in assigned and float(row[j]) + 1e-7 >= threshold]
                if not members:
                    continue
                members.insert(0, representative)
                assigned.update(members)
                items = [{**bucket['items'][j], 'similarityToRepresentative': min(1., float(row[j]))} for j in members]
                groups.append({'id': 'similar-' + fingerprint({'space': space, 'items': items})[:24],
                               'modelSpace': bucket['spec'], 'members': items})
    return {'groups': groups, 'itemsCompared': count, 'modelSpaces': len(spaces),
            'threshold': threshold, 'truncated': truncated, 'excluded': excluded,
            'note': '相似分组仅供查看；未合并身份、修改来源或删除任何媒体'}
