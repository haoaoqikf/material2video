"""显式 URL/本地候选登记；locator 只在本次调用内使用，不扫描或存放私人路径。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging
import stat
from urllib.parse import parse_qsl, unquote, urlsplit
from uuid import uuid4

from m2v.core.media_policy import SourceMetadata, Usage
from .contracts import Requirement, Source, SourceData, fingerprint, identity
from .errors import MaterialError
from .network import public_url, validate_url
from .paths import no_links
from .source_catalog import put_source
from .source_types import page_url, snapshot, text, variant
from .store import MaterialStore


logger = logging.getLogger(__name__)

_PENDING = '页面/文件候选尚未取得或探测，不表示可直接入片'
_VOLATILE = '临时或未知地址参数未保存；后续获取须显式重提供原地址，不能从脱敏 URL 猜资源'


@dataclass(frozen=True)
class PublicReference:
    url: str | None
    external_id: str | None
    title: str
    requires_locator: bool


@dataclass(frozen=True)
class RegisteredSource:
    document: Source
    locator: str | Path = field(repr=False)
    local: bool = False
    stamp: str | None = None


def _stamp(path, info) -> str:
    return fingerprint({'name': path.name, 'bytes': info.st_size, 'mtimeNs': info.st_mtime_ns,
                        'device': info.st_dev, 'fileId': info.st_ino})


def _inspect_local(value):
    path = Path(value)
    # 必须在 lstat 前拒绝 UNC/设备命名空间，不能把“本地输入”变成隐式 SMB 会话。
    parts = path.parts[1:] if path.anchor else path.parts
    if str(path).startswith(('\\\\', '//')) or any(':' in part for part in parts):
        raise MaterialError('security-blocked', '本地素材不接受 UNC、设备或 ADS 路径，请先复制到本地普通文件', stage='sources')
    try:
        path = no_links(path, stage='sources')
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise MaterialError('invalid-request', '需要显式普通文件，不接受目录或设备', stage='sources')
        if not info.st_size:
            raise MaterialError('media-invalid', '本地素材文件为空', stage='sources')
    except OSError:
        raise MaterialError('not-found', '指定本地素材不可访问', stage='sources') from None
    return path, info


def local_file(value: Path | str) -> Path:
    return _inspect_local(value)[0]


def file_stamp(value: Path | str) -> str:
    return _stamp(*_inspect_local(value))


def register_local(value: Path | str, *, store: MaterialStore | None = None, title=None,
                   author=None, license=None, references=()) -> RegisteredSource:
    path, info = _inspect_local(value)
    stamp = _stamp(path, info)
    data = SourceData(provider='local', externalId=identity('local-file', {'stamp': stamp}),
        title=text(title) or text(path.name) or '显式本地候选', author=text(author) or '未知', license=text(license) or '未知',
        state='registered', variants=[variant('original', None, kind='unknown', size=info.st_size)],
        limitations=['本地候选未探测或复制；跨调用重新获取时须显式提供原文件，不从私人目录反查'],
        policy=SourceMetadata(sourceType='other', publisher=text(author) or '未知', usage=Usage(status='not-checked')))
    document = put_source(store, snapshot(data), references)
    logger.info('显式本地候选登记 id=%s bytes=%d', document.id, info.st_size)
    return RegisteredSource(document, path, True, stamp)


def public_reference(value: str) -> PublicReference:
    locator = validate_url(value).url
    public = page_url(locator)
    # 长路径段本身也可能是 bearer token；未知链接不把 redacted 假地址伪装成可重放来源。
    if '[redacted]' in public_url(public):
        public = None
    original_parts, safe_parts = urlsplit(locator), urlsplit(public or '')
    changed = public is None or parse_qsl(original_parts.query, keep_blank_values=True) != parse_qsl(safe_parts.query, keep_blank_values=True)
    basename = unquote(safe_parts.path.rsplit('/', 1)[-1]) if public else ''
    return PublicReference(public, identity('url', {'url': public}) if public and not changed else None,
                           text(basename) or '显式链接候选', changed)


def page_limitations(previous, *, requires_locator=False):
    notes = [item for item in previous if item not in {_PENDING, _VOLATILE}]
    notes.append('已解析静态页面声明；媒体本体尚未获取/探测，不表示可直接入片')
    if requires_locator:
        notes.append(_VOLATILE)
    return list(dict.fromkeys(notes))


def register_url(value: str, *, store: MaterialStore | None = None, mode: str = 'page', title=None,
                 author=None, license=None, references=()) -> RegisteredSource:
    if mode not in {'page', 'file', 'auto'}:
        raise MaterialError('invalid-request', 'URL 登记模式必须为 page/file/auto', stage='sources')
    locator = validate_url(value).url
    reference = public_reference(locator)
    limitations = [_PENDING] + ([_VOLATILE] if reference.requires_locator else [])
    provider = {'page': 'webpage', 'file': 'http-file', 'auto': 'url'}[mode]
    data = SourceData(provider=provider, externalId=reference.external_id,
        sourceUrl=reference.url, title=text(title) or reference.title, author=text(author) or '未知',
        license=text(license) or '未知', state='limited' if reference.requires_locator else 'registered', limitations=limitations,
        variants=[variant('original', locator, kind='unknown')] if mode == 'file' else [],
        policy=SourceMetadata(sourceType='other', publisher=text(author) or '未知', usage=Usage(status='not-checked')))
    # 无可公开稳定身份时不将两个同路径的未知 query 资源合并，也不持久化 query 的哈希身份。
    document = put_source(store, snapshot(data), references, nonce=uuid4().hex if reference.requires_locator else None)
    logger.info('显式链接候选登记 id=%s mode=%s temporary=%s', document.id, mode, reference.requires_locator)
    return RegisteredSource(document, locator)


def source_gap(requirement: Requirement | None = None) -> list[str]:
    data = requirement.data if requirement is not None else None
    entity = text(data.identity.entity or data.identity.event) if data is not None else ''
    entity = entity or '目标对象'
    advice = [f'沿 {entity} 的原始发布者、官方账号或可追溯档案补查；同类图库画面不等于该对象实录',
              '若仍不可得，将缺口反馈到现有文案/场景设计，收窄主张或明确示意；不以无关动态补事实']
    if data is not None and (data.task == 'process' or data.actions or data.minDurationUs > 0):
        advice.append('检查完整连续动作窗口；字幕提及、画面相似和切镜不等于动作已出现或过程完整')
    advice.append('会话/访问受限可显式提供会话文件或本地素材；不自动读取日常浏览器或绕过访问控制')
    return advice
