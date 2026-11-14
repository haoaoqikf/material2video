"""素材工作层统一、可安全展示的错误。"""
from __future__ import annotations

from m2v.core.errors import M2VError


class MaterialError(M2VError):
    """message 必须是调用方已脱敏的说明，不能直接拼接远端异常。"""

    def __init__(self, code: str, message: str, *, stage: str = 'materials',
                 retryable: bool = False, source_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.retryable = retryable
        self.source_id = source_id

    def to_dict(self) -> dict:
        return {'code': self.code, 'stage': self.stage, 'retryable': self.retryable,
                'sourceId': self.source_id, 'message': str(self)}
