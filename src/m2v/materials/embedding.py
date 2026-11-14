"""本地 E5 文本与 SigLIP 2 视觉编码；只用已校验模型，显式 CPU、无远端代码。

返回 float32、已 L2 归一化的向量；不同模型、预处理或维数不得混用。
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np

from .errors import MaterialError
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

TEXT_MODEL = 'e5-small'
VISUAL_MODEL = 'siglip2-base'
MAX_TEXT_CHARS = 2000


def require_runtime() -> None:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        raise MaterialError('dependency-missing', '文本/视觉索引需要可选依赖；请安装 extra：semantic、vision',
                            stage='models') from exc


@lru_cache(maxsize=2)
def _text_backbone(path: str):
    require_runtime()
    import torch
    from transformers import AutoModel, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model = AutoModel.from_pretrained(path, local_files_only=True, trust_remote_code=False,
                                      use_safetensors=True)
    model.eval()
    return tokenizer, model, torch


@lru_cache(maxsize=1)
def _visual_backbone(path: str):
    require_runtime()
    import torch
    from transformers import AutoModel, AutoProcessor
    processor = AutoProcessor.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model = AutoModel.from_pretrained(path, local_files_only=True, trust_remote_code=False,
                                      use_safetensors=True)
    model.eval()
    return processor, model, torch


def _pooled(value) -> np.ndarray:
    """兼容 transformers 5.x 返回 ModelOutput 与返回张量两种签名。"""
    tensor = value if hasattr(value, 'dtype') else getattr(value, 'pooler_output', None)
    if tensor is None:
        raise MaterialError('model-missing', '视觉/文本模型未返回可用的池化向量', stage='index')
    return tensor.float().cpu().numpy()


def _normalize(array: np.ndarray) -> np.ndarray:
    array = np.ascontiguousarray(array, dtype='float32')
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if not np.all(np.isfinite(array)) or np.any(norms == 0):
        raise MaterialError('media-invalid', '模型输出含非有限值或零向量，未发布索引', stage='index')
    return array / norms


def embed_texts(manager: ModelManager, texts: list[str], *, prefix: str,
                batch_size: int = 16) -> np.ndarray:
    if prefix not in {'query', 'passage'}:
        raise MaterialError('invalid-request', 'E5 前缀必须是 query 或 passage', stage='index')
    if not texts or type(batch_size) is not int or not 1 <= batch_size <= 64:
        raise MaterialError('invalid-request', '文本向量批次或输入无效', stage='index')
    tokenizer, model, torch = _text_backbone(str(manager.path(TEXT_MODEL)))
    prepared = [f'{prefix}: {value[:MAX_TEXT_CHARS]}' for value in texts]
    output = []
    with torch.no_grad():
        for start in range(0, len(prepared), batch_size):
            batch = prepared[start:start + batch_size]
            encoded = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors='pt')
            hidden = model(**encoded).last_hidden_state
            mask = encoded['attention_mask'].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            output.append(pooled.float().cpu().numpy())
    return _normalize(np.vstack(output))


def embed_images(manager: ModelManager, paths: list[Path], *, batch_size: int = 8) -> np.ndarray:
    if not paths or type(batch_size) is not int or not 1 <= batch_size <= 16:
        raise MaterialError('invalid-request', '视觉向量批次或输入无效', stage='index')
    processor, model, torch = _visual_backbone(str(manager.path(VISUAL_MODEL)))
    from PIL import Image
    output = []
    with torch.no_grad():
        for start in range(0, len(paths), batch_size):
            images = []
            for path in paths[start:start + batch_size]:
                try:
                    with Image.open(path) as picture:
                        images.append(picture.convert('RGB'))
                except OSError as exc:
                    raise MaterialError('decode-failed', '关键帧无法解码，未发布视觉索引', stage='index') from exc
            inputs = processor(images=images, return_tensors='pt')
            output.append(_pooled(model.get_image_features(**inputs)))
    return _normalize(np.vstack(output))


def embed_visual_text(manager: ModelManager, texts: list[str]) -> np.ndarray:
    if not texts:
        raise MaterialError('invalid-request', '视觉文本查询为空', stage='find')
    processor, model, torch = _visual_backbone(str(manager.path(VISUAL_MODEL)))
    output = []
    with torch.no_grad():
        for start in range(0, len(texts), 8):
            batch = [value[:MAX_TEXT_CHARS] for value in texts[start:start + 8]]
            # SigLIP 以固定长度 padding 且不加注意力掩码训练；额外掩码会显著破坏图文对齐。
            inputs = processor(text=batch, padding='max_length', truncation=True, return_tensors='pt')
            output.append(_pooled(model.get_text_features(**inputs)))
    return _normalize(np.vstack(output))


def model_identity(manager: ModelManager, name: str) -> dict:
    identity = manager.identity(name)
    return {'model': name, 'repoId': identity['repoId'], 'revision': identity['revision'],
            'license': identity['license'], 'preprocessing': identity['preprocessing'],
            'files': identity['files']}


def dimensions(manager: ModelManager, name: str) -> int:
    spec = manager.registry['models'][name]
    value = spec.get('dimensions')
    if type(value) is not int or value <= 0:
        raise MaterialError('invalid-request', f'模型 {name} 未登记向量维数', stage='index')
    return value
