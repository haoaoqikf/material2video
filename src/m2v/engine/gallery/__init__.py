"""共享在线图库层：把「关键词 → 候选素材」与「候选 → 本地文件」收敛到一处。

文章 v6 的混合媒体镜头可以来自助手全网检索，也可以来自 Pexels、Pixabay 这类
可选图库；两种来源共用同一套候选记录、长宽比判定与下载限制，因此图库适配器
从旧的独立素材类型上移到引擎层，供文章导入边界直接复用。

网络访问全部走可注入的 :class:`Transport`：生产用标准库 ``urllib``（不新增依赖），
测试用本机假图库服务，因此检索与下载这条链路可以完全离线验证。
"""
from m2v.engine.gallery.aspect import (
    DEFAULT_TOLERANCE,
    MODES,
    MODE_ANY,
    MODE_CANVAS,
    canvas_ratio,
    describe_ratio,
    effective_mode,
    ratio_matches,
    target_ratio,
    tolerance_of,
)
from m2v.engine.gallery.pixabay import PIXABAY_LICENSE, PixabayProvider
from m2v.engine.gallery.provider import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_DOWNLOAD_BYTES,
    PEXELS_LICENSE,
    PHOTO_SUFFIXES,
    PROVIDER_DEFAULTS,
    PROVIDERS,
    VIDEO_SUFFIXES,
    Candidate,
    HttpTransport,
    PexelsProvider,
    Transport,
    build,
    pick_variant,
)

__all__ = [
    "Candidate", "Transport", "HttpTransport", "PexelsProvider", "PixabayProvider",
    "PROVIDERS", "PROVIDER_DEFAULTS", "build", "pick_variant",
    "MAX_DOWNLOAD_BYTES", "DEFAULT_TIMEOUT_SECONDS", "VIDEO_SUFFIXES", "PHOTO_SUFFIXES",
    "PEXELS_LICENSE", "PIXABAY_LICENSE",
    "canvas_ratio", "effective_mode", "target_ratio", "tolerance_of", "ratio_matches",
    "describe_ratio", "MODE_CANVAS", "MODE_ANY", "MODES", "DEFAULT_TOLERANCE",
]
