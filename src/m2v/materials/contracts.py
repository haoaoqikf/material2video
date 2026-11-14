"""独立、严格的素材工作材料 v1；不改变正式作品和媒体登记契约。

所有时间区间为整数微秒半开区间。模型分数、召回理由和实际观察分开，
避免把算法命中隐式提升为人物身份、完整动作或独立评审的通过结论。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal, Union
from urllib.parse import urlsplit

from pydantic import Field, JsonValue, StringConstraints, TypeAdapter, ValidationError, field_validator, model_validator

from m2v.core.media_policy import SourceMetadata
from m2v.core.schema import NonEmptyText, StrictModel
from .errors import MaterialError

Identifier = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')]
Sha256 = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
Microseconds = Annotated[int, Field(ge=0)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Channel = Literal['captions', 'asr', 'ocr', 'chapters', 'metadata', 'shots', 'frames', 'text', 'visual']


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def canonical(value) -> str:
    if isinstance(value, StrictModel):
        value = value.model_dump(mode='json')
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def identity(prefix: str, value) -> str:
    return f'{prefix}-{fingerprint(value)[:32]}'


def relative_path(value: str) -> str:
    """使用跨平台交集，拒绝 Windows ADS/盘符以及被 Path 自动折叠的路径。"""
    if (not value or '\\' in value or ':' in value or '\x00' in value
            or PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()
            or any(p in {'', '.', '..'} for p in value.split('/'))):
        raise ValueError('必须是无链接、无越界的 POSIX 相对路径')
    return value


def public_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        split = urlsplit(value)
        if (split.scheme not in {'http', 'https'} or not split.hostname or split.username
                or split.password or re.search(r'[\x00-\x20\x7f]', value)):
            raise ValueError
        _ = split.port
    except ValueError as exc:
        raise ValueError('需要无内嵌凭据的 HTTP(S) 来源地址') from exc
    return value


class MaterialModel(StrictModel):
    @model_validator(mode='before')
    @classmethod
    def finite_json(cls, value):
        def check(item):
            if isinstance(item, StrictModel):
                check(item.model_dump(mode='python'))
            elif isinstance(item, float) and not math.isfinite(item):
                raise ValueError('素材材料不允许非有限数值')
            elif isinstance(item, dict):
                for child in item.values():
                    check(child)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    check(child)
        check(value)
        return value


class TimeRange(MaterialModel):
    startUs: Microseconds
    endUs: Microseconds

    @model_validator(mode='after')
    def ordered(self):
        if self.endUs <= self.startUs:
            raise ValueError('半开区间结束必须晚于开始')
        return self


class TimeBase(MaterialModel):
    num: Annotated[int, Field(gt=0)]
    den: Annotated[int, Field(gt=0)]


class SourceMapping(MaterialModel):
    status: Literal['verified', 'estimated', 'unknown'] = 'unknown'
    method: NonEmptyText = 'unknown'
    sourceOriginUs: Microseconds | None = None
    rateNum: Annotated[int, Field(gt=0)] = 1
    rateDen: Annotated[int, Field(gt=0)] = 1
    maxErrorUs: Microseconds | None = None

    @model_validator(mode='after')
    def honest(self):
        if self.status == 'unknown' and self.sourceOriginUs is not None:
            raise ValueError('未知映射不能声明源原点')
        if self.status != 'unknown' and self.sourceOriginUs is None:
            raise ValueError('非未知映射必须有依据的源原点')
        if self.status == 'verified' and self.maxErrorUs is None:
            raise ValueError('已验证映射必须声明误差')
        return self


class Timeline(MaterialModel):
    localOriginPts: int | None = None
    timeBase: TimeBase | None = None
    sourceMapping: SourceMapping = Field(default_factory=SourceMapping)

    def source_range(self, interval: TimeRange | None) -> TimeRange | None:
        """估计坐标不作为精确源区间导出；依据仍留在映射本身。"""
        mapping = self.sourceMapping
        if interval is None or mapping.status != 'verified':
            return None
        origin = mapping.sourceOriginUs
        assert origin is not None
        return TimeRange(startUs=origin + interval.startUs * mapping.rateNum // mapping.rateDen,
                         endUs=origin + interval.endUs * mapping.rateNum // mapping.rateDen)


class Artifact(MaterialModel):
    path: NonEmptyText
    sha256: Sha256
    bytes: Annotated[int, Field(ge=0)]
    _path = field_validator('path')(relative_path)


class Probe(MaterialModel):
    kind: Literal['image', 'video', 'audio']
    container: NonEmptyText
    width: Annotated[int, Field(gt=0)] | None = None
    height: Annotated[int, Field(gt=0)] | None = None
    durationUs: Annotated[int, Field(gt=0)] | None = None
    fps: TimeBase | None = None
    hasAudio: bool = False
    sampleRate: Annotated[int, Field(gt=0)] | None = None
    audioChannels: Annotated[int, Field(gt=0)] | None = None
    videoStartUs: int | None = None
    audioStartUs: int | None = None
    timeline: Timeline = Field(default_factory=Timeline)

    @model_validator(mode='after')
    def media_dimensions(self):
        if self.kind != 'audio' and (self.width is None or self.height is None):
            raise ValueError('图像和视频必须有实测尺寸')
        if self.kind == 'image' and self.durationUs is not None:
            raise ValueError('图片没有媒体时长')
        if self.kind != 'image' and self.durationUs is None:
            raise ValueError('时基媒体必须有实测时长')
        return self


class Query(MaterialModel):
    text: NonEmptyText
    language: NonEmptyText | None = None


class IdentityConstraint(MaterialModel):
    entity: NonEmptyText | None = None
    event: NonEmptyText | None = None
    place: NonEmptyText | None = None
    dateRange: NonEmptyText | None = None
    mustMatch: bool = False


class RequirementData(MaterialModel):
    text: NonEmptyText
    task: Literal['evidence', 'identity', 'process', 'explanation', 'mood'] = 'explanation'
    subjects: list[NonEmptyText] = Field(default_factory=list)
    actions: list[NonEmptyText] = Field(default_factory=list)
    identity: IdentityConstraint = Field(default_factory=IdentityConstraint)
    queries: list[Query] = Field(default_factory=list)
    minDurationUs: Microseconds = 0
    preferredOrientation: Literal['landscape', 'portrait', 'square'] | None = None
    allowIllustrative: bool = True
    sceneId: Identifier | None = None


class Variant(MaterialModel):
    id: NonEmptyText
    url: NonEmptyText | None = None
    kind: Literal['image', 'video', 'audio', 'subtitle', 'unknown'] = 'unknown'
    width: Annotated[int, Field(gt=0)] | None = None
    height: Annotated[int, Field(gt=0)] | None = None
    bytes: Annotated[int, Field(ge=0)] | None = None
    mime: NonEmptyText | None = None
    _url = field_validator('url')(public_url)


class SourceData(MaterialModel):
    provider: NonEmptyText
    externalId: NonEmptyText | None = None
    sourceUrl: NonEmptyText | None = None
    title: NonEmptyText
    author: NonEmptyText = '未知'
    license: NonEmptyText = '未知'
    publishedAt: NonEmptyText | None = None
    policy: SourceMetadata = Field(default_factory=SourceMetadata)
    variants: list[Variant] = Field(default_factory=list)
    queries: list[Query] = Field(default_factory=list)
    metadataSnapshotSha256: Sha256 | None = None
    state: Literal['discovered', 'registered', 'limited'] = 'discovered'
    limitations: list[NonEmptyText] = Field(default_factory=list)
    _url = field_validator('sourceUrl')(public_url)

    @model_validator(mode='after')
    def unique_variants(self):
        if len({item.id for item in self.variants}) != len(self.variants):
            raise ValueError('同一来源的规格 ID 不能重复')
        return self


class CaptionTrack(MaterialModel):
    artifact: Artifact
    language: NonEmptyText | None = None
    origin: Literal['manual', 'automatic', 'local', 'asr']
    alignment: Literal['verified', 'unverified'] = 'unverified'
    format: Literal['srt', 'vtt', 'ass', 'json']


class Chapter(MaterialModel):
    title: NonEmptyText
    localRange: TimeRange


class MediaData(MaterialModel):
    sourceId: Identifier
    artifact: Artifact
    probe: Probe
    variant: NonEmptyText = 'original'
    coverage: Literal['full', 'section', 'unknown'] = 'unknown'
    requestedRange: TimeRange | None = None
    observedRange: TimeRange | None = None
    upstreamFullSha256: Sha256 | None = None
    fetchIdentity: Sha256
    toolchain: dict[str, JsonValue] = Field(default_factory=dict)
    captions: list[CaptionTrack] = Field(default_factory=list)
    chapters: list[Chapter] = Field(default_factory=list)

    @model_validator(mode='after')
    def known_coverage(self):
        if self.coverage != 'full' and self.upstreamFullSha256 is not None:
            raise ValueError('未取得整片不能声明整片摘要')
        if self.coverage == 'full' and self.upstreamFullSha256 not in {None, self.artifact.sha256}:
            raise ValueError('整片摘要与实际媒体不一致')
        if self.probe.kind == 'image' and any((self.requestedRange, self.observedRange, self.chapters)):
            raise ValueError('图片不能声明视频时间区间')
        duration = self.probe.durationUs
        if duration is not None and any(ch.localRange.endUs > duration for ch in self.chapters):
            raise ValueError('章节越过实际媒体时长')
        return self


class EmbeddingSpec(MaterialModel):
    model: NonEmptyText
    revision: NonEmptyText
    weightsSha256: Sha256
    preprocessing: NonEmptyText
    dimensions: Annotated[int, Field(gt=0)]
    normalized: bool = True
    dtype: Literal['float32'] = 'float32'
    device: NonEmptyText = 'cpu'
    precision: NonEmptyText = 'float32'


class IndexData(MaterialModel):
    mediaId: Identifier
    mediaSha256: Sha256
    channel: Channel
    status: Literal['building', 'complete', 'failed']
    config: dict[str, JsonValue] = Field(default_factory=dict)
    configSha256: Sha256
    inputDigests: list[Sha256] = Field(default_factory=list)
    toolchain: dict[str, JsonValue] = Field(default_factory=dict)
    timelineMappingSha256: Sha256
    artifacts: list[Artifact] = Field(default_factory=list)
    recordCount: Annotated[int, Field(ge=0)] = 0
    embeddingSpec: EmbeddingSpec | None = None
    failure: NonEmptyText | None = None

    @model_validator(mode='after')
    def complete_outputs(self):
        if self.status == 'complete' and (not self.artifacts or self.failure is not None):
            raise ValueError('完成索引必须有有效输出且无失败状态')
        if self.status == 'failed' and self.failure is None:
            raise ValueError('失败索引必须有失败原因')
        return self


class TextBox(MaterialModel):
    text: NonEmptyText
    polygon: Annotated[list[Annotated[list[Finite], Field(min_length=2, max_length=2)]], Field(min_length=4, max_length=4)]
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class WordTiming(MaterialModel):
    text: NonEmptyText
    localRange: TimeRange
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None


class IndexRecord(MaterialModel):
    id: Identifier
    channel: Channel
    text: str = ''
    localRange: TimeRange | None = None
    frame: Artifact | None = None
    language: NonEmptyText | None = None
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    boxes: list[TextBox] = Field(default_factory=list)
    words: list[WordTiming] = Field(default_factory=list)
    vectorRow: Annotated[int, Field(ge=0)] | None = None
    alignment: Literal['verified', 'unverified', 'not-applicable'] = 'unverified'
    origin: NonEmptyText

    @model_validator(mode='after')
    def word_windows(self):
        if self.words and self.localRange is None:
            raise ValueError('词时间码必须有所属记录的时间窗口')
        if self.localRange is not None and any(
                word.localRange.startUs < self.localRange.startUs or word.localRange.endUs > self.localRange.endUs
                for word in self.words):
            raise ValueError('词时间码不能越过所属记录窗口')
        return self


class Observation(MaterialModel):
    status: Literal['observed', 'not-observed', 'unknown'] = 'unknown'
    basis: str = ''
    observer: NonEmptyText | None = None
    localRange: TimeRange | None = None

    @model_validator(mode='after')
    def evidence(self):
        if self.status != 'unknown' and (not self.basis.strip() or self.observer is None):
            raise ValueError('实际观察必须有依据和观察者')
        return self


class Observations(MaterialModel):
    subjectMatch: Observation = Field(default_factory=Observation)
    actionVisible: Observation = Field(default_factory=Observation)
    actionComplete: Observation = Field(default_factory=Observation)
    cropUsable: Observation = Field(default_factory=Observation)
    factualIdentityMatch: Observation = Field(default_factory=Observation)


class RetrievalReason(MaterialModel):
    channel: Channel
    rank: Annotated[int, Field(gt=0)]
    score: Finite
    excerpt: str = ''
    recordId: Identifier | None = None
    frame: Artifact | None = None
    modelIdentity: NonEmptyText | None = None


class CandidateData(MaterialModel):
    requirementId: Identifier
    requirementDigest: Sha256
    sourceId: Identifier
    mediaId: Identifier
    mediaSha256: Sha256
    indexIds: list[Identifier]
    localRange: TimeRange | None
    sourceRange: TimeRange | None = None
    timelineMappingSha256: Sha256
    retrievalReasons: Annotated[list[RetrievalReason], Field(min_length=1)]
    fusionScore: Finite
    observations: Observations = Field(default_factory=Observations)
    previews: list[Artifact] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)


class Transform(MaterialModel):
    fps: TimeBase = Field(default_factory=lambda: TimeBase(num=30, den=1))
    audio: Literal['preserve', 'discard'] = 'preserve'
    codec: Literal['libx264'] = 'libx264'
    crf: Annotated[int, Field(ge=0, le=51)] = 18


class SelectionData(MaterialModel):
    candidateId: Identifier
    candidateDigest: Sha256
    mediaId: Identifier
    mediaSha256: Sha256
    localRange: TimeRange | None
    sourceRange: TimeRange | None = None
    decision: Literal['chosen', 'rejected']
    rationale: NonEmptyText
    purpose: NonEmptyText
    operator: NonEmptyText
    observations: Observations = Field(default_factory=Observations)
    transform: Transform = Field(default_factory=Transform)
    outputArtifact: Artifact | None = None
    outputProbe: Probe | None = None
    toolchain: dict[str, JsonValue] = Field(default_factory=dict)


class ReceiptData(MaterialModel):
    operationId: Identifier
    selectionId: Identifier
    selectionDigest: Sha256
    sourceId: Identifier
    sourceUrl: NonEmptyText | None = None
    inputMediaSha256: Sha256
    upstreamFullSha256: Sha256 | None = None
    localRange: TimeRange | None
    sourceRange: TimeRange | None = None
    timeline: Timeline
    outputArtifactSha256: Sha256
    manifestSha256: Sha256
    targetProjectId: NonEmptyText
    targetAssetId: Identifier
    targetAssetPath: NonEmptyText | None = None
    targetAssetSha256: Sha256 | None = None
    registeredEntryDigest: Sha256 | None = None
    status: Literal['pending', 'committed', 'failed']
    failure: NonEmptyText | None = None
    committedAt: NonEmptyText | None = None
    _url = field_validator('sourceUrl')(public_url)

    @field_validator('targetAssetPath')
    @classmethod
    def safe_target(cls, value):
        return relative_path(value) if value is not None else None

    @model_validator(mode='after')
    def committed_identity(self):
        if self.status == 'committed' and any(value is None for value in
                (self.targetAssetPath, self.targetAssetSha256, self.registeredEntryDigest, self.committedAt)):
            raise ValueError('完成凭据必须绑定正式登记和提交时间')
        if self.sourceRange != self.timeline.source_range(self.localRange):
            raise ValueError('源区间必须与本地窗口的已验证映射完全一致')
        return self


class Document(MaterialModel):
    schemaVersion: Literal[1] = 1
    id: Identifier
    createdAt: NonEmptyText = Field(default_factory=utc_now)

    @field_validator('createdAt')
    @classmethod
    def timestamp(cls, value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            raise ValueError('创建时间必须有时区')
        return value

    @field_validator('schemaVersion', mode='before')
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError('schemaVersion 必须是整数')
        return value


class Requirement(Document):
    kind: Literal['material.requirement'] = 'material.requirement'
    data: RequirementData


class Source(Document):
    kind: Literal['material.source'] = 'material.source'
    data: SourceData


class Media(Document):
    kind: Literal['material.media'] = 'material.media'
    data: MediaData


class Index(Document):
    kind: Literal['material.index'] = 'material.index'
    data: IndexData


class Candidate(Document):
    kind: Literal['material.candidate'] = 'material.candidate'
    data: CandidateData


class Selection(Document):
    kind: Literal['material.selection'] = 'material.selection'
    data: SelectionData


class Receipt(Document):
    kind: Literal['material.receipt'] = 'material.receipt'
    data: ReceiptData


WorkDocument = Annotated[Union[Requirement, Source, Media, Index, Candidate, Selection, Receipt], Field(discriminator='kind')]
DOCUMENT = TypeAdapter(WorkDocument)


class Collection(Document):
    """版本化集合只装同种记录，条目仍保留自己的独立身份与版本。"""
    kind: Literal['material.requirements', 'material.sources', 'material.media-list',
                  'material.indices', 'material.candidates', 'material.selections', 'material.receipts']
    data: list[WorkDocument]

    @model_validator(mode='after')
    def homogeneous(self):
        singular = {'material.requirements': 'material.requirement', 'material.sources': 'material.source',
                    'material.media-list': 'material.media', 'material.indices': 'material.index',
                    'material.candidates': 'material.candidate', 'material.selections': 'material.selection',
                    'material.receipts': 'material.receipt'}[self.kind]
        if any(item.kind != singular for item in self.data) or len({item.id for item in self.data}) != len(self.data):
            raise ValueError('集合种类必须一致且条目 ID 不能重复')
        return self


def parse_collection(value: dict) -> Collection:
    try:
        return Collection.model_validate(value)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = '.'.join(str(item) for item in first['loc'])
        raise MaterialError('invalid-request', f'素材工作集合 {location}: {first["type"]}', stage='contract') from None


def parse_document(value: dict) -> WorkDocument:
    try:
        return DOCUMENT.validate_python(value)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = '.'.join(str(item) for item in first['loc'])
        # 不包含 input/ctx，避免任意外部内容或敏感链接被异常回显。
        raise MaterialError('invalid-request', f'素材工作材料 {location}: {first["type"]}', stage='contract') from None
