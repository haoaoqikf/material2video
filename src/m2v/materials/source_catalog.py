"""来源文档的不可变发布；来源适配和显式登记共用同一身份规则。"""
from __future__ import annotations

from collections.abc import Iterable

from .contracts import Source, SourceData, identity
from .errors import MaterialError
from .store import MaterialStore


def put_source(store: MaterialStore | None, data: SourceData, references: Iterable[str] = (), *,
               nonce: str | None = None) -> Source:
    data = SourceData.model_validate(data.model_dump(mode='json'))
    refs = set(references)
    # 引用域沿用已发布的来源 ID 算法，不因抽取共用函数而让旧快照身份漂移。
    payload = {'data': data.model_dump(mode='json'), 'requirements': sorted(refs)}
    if nonce is not None:
        payload['registration'] = nonce
    document_id = identity('source', payload)
    if store is not None:
        try:
            previous = store.get(document_id, kind='material.source')
        except MaterialError as exc:
            if exc.code != 'not-found':
                raise
        else:
            if previous.data != data:
                raise MaterialError('conflict', '来源内容与不可变身份不一致', stage='sources')
            return store.put(previous, references=refs)
    result = Source(id=document_id, data=data)
    return store.put(result, references=refs) if store is not None else result
