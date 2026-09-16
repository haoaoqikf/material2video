"""文章归属推导与标准输出路径。

每篇文章占一个稳定目录，源文件入 Git，产物写入 `outputs/`：

```text
<root>/videos/<slug>/{article.md, storyboard.json, index.html}
<root>/examples/<slug>/...              # 与 videos/ 同构的示例
<root>/outputs/<slug>/{silent,voiced}.mp4, voiced.srt, media/, previews/
<root>/outputs/examples/<slug>/...      # 示例产物独立一层，避免与实际文章同名冲突
```

本模块集中实现推导规则，命令行只做参数默认值与报错，不再各自拼路径。
所有推导都从输入文件的位置向上查找，与执行命令时的工作目录无关。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import storyboard as sb
from .errors import A2VError

logger = logging.getLogger(__name__)

# 项目根标记：skill 主文档的位置。它同时是「这个目录属于 article2video 项目」的证据。
PROJECT_MARKER = Path(".agents/skills/article2video/SKILL.md")

# 源文件的两种归属目录，直接挂在项目根下。
SOURCE_KINDS: dict[str, str] = {"videos": "article", "examples": "example"}

# 产物根目录名（已被 .gitignore 忽略）。
OUTPUTS_DIR = "outputs"

# 成片文件名固定，同类重复导出即覆盖同一个文件。
SILENT_NAME = "silent.mp4"
VOICED_NAME = "voiced.mp4"
PREVIEW_DIR = "previews"
MEDIA_DIR = "media"

ArticleKind = Literal["article", "example"]


@dataclass(frozen=True)
class ArticlePaths:
    """一篇文章的源目录与产物目录。

    字段都是绝对路径；`output_dir` 只表示位置，不保证已经存在。
    """

    root: Path
    kind: ArticleKind
    source_dir: Path
    output_dir: Path

    @property
    def slug(self) -> str:
        return self.source_dir.name

    @property
    def media_dir(self) -> Path:
        return self.output_dir / MEDIA_DIR

    @property
    def media_manifest(self) -> Path:
        return self.media_dir / "media.json"

    @property
    def preview_dir(self) -> Path:
        return self.output_dir / PREVIEW_DIR

    def render_output(self, voiced: bool, preview: bool = False) -> Path:
        """成片路径：限帧试渲染写入 `previews/`，使用相同的成片文件名。"""
        name = VOICED_NAME if voiced else SILENT_NAME
        return (self.preview_dir if preview else self.output_dir) / name


def project_root(path: str | Path) -> Path:
    """从文件或目录位置向上查找项目根目录。

    以 `.agents/skills/article2video/SKILL.md` 为标记，而不是 `.git`：
    标记文件兼作「此处是 article2video 项目根」的判据，避免把任意 Git 仓库
    的顶层目录误认为项目根。找不到时抛出 A2VError，由调用方补充上下文。
    """
    candidate = Path(path)
    if candidate.is_file():
        candidate = candidate.parent
    try:
        start = candidate.resolve()
    except OSError as exc:  # 路径不可解析时不猜测，交给调用方报错
        raise A2VError(f"无法解析路径 {candidate}: {exc}") from exc
    for directory in (start, *start.parents):
        if (directory / PROJECT_MARKER).is_file():
            return directory
    raise A2VError(
        f"未找到项目根目录：{start} 及其上级都没有 {PROJECT_MARKER.as_posix()}，"
        "无法推导文章归属，请显式指定输出路径"
    )


def locate_article(root: str | Path, path: str | Path) -> tuple[ArticleKind, str]:
    """判定 `path` 属于哪个文章目录，返回 (类型, slug)。

    `path` 可以是文章目录本身，也可以是它内部的任意文件（例如
    `videos/<slug>/assets/page.html` 仍归属该文章）。判据是祖先中存在
    `<root>/videos/<slug>` 或 `<root>/examples/<slug>`；再深的层级不会被
    误判成 slug，因为 slug 必须直接挂在 `videos/` 或 `examples/` 下。
    """
    root = Path(root).resolve()
    candidate = Path(path)
    start = candidate if candidate.is_dir() else candidate.parent
    try:
        current = start.resolve()
    except OSError as exc:
        raise A2VError(f"无法解析路径 {start}: {exc}") from exc

    for directory in (current, *current.parents):
        # 文章目录是 slug 那一层，相对 root 恰好两段：<videos|examples>/<slug>。
        # 因此判据是「父目录名属于 videos/examples，且 slug 目录直接挂在 root 下」，
        # 而不是「这个目录本身叫 videos/examples」。
        kind = SOURCE_KINDS.get(directory.parent.name)
        if kind is not None and _depth_under(root, directory) == 2:
            return kind, directory.name  # type: ignore[return-value]

    raise A2VError(
        f"无法推导文章归属：{start} 不是项目根下的 videos/<slug>/ 或 examples/<slug>/，"
        "请使用规范目录或显式指定输出路径"
    )


def _depth_under(root: Path, directory: Path) -> int:
    """directory 相对 root 的层级数；不在 root 之下时返回 -1。"""
    try:
        return len(directory.relative_to(root).parts)
    except ValueError:
        return -1


def article_paths(root: str | Path, path: str | Path) -> ArticlePaths:
    """组合出文章的源目录与产物目录。"""
    root = Path(root).resolve()
    kind, slug = locate_article(root, path)
    output_dir = root / OUTPUTS_DIR
    if kind == "example":
        # 示例产物独立一层，避免与同名实际文章的产物互相覆盖
        output_dir = output_dir / "examples"
    return ArticlePaths(
        root=root,
        kind=kind,
        source_dir=root / source_dir_name(kind) / slug,
        output_dir=output_dir / slug,
    )


def source_dir_name(kind: ArticleKind) -> str:
    """归属类型对应的源目录名。SOURCE_KINDS 是唯一权威定义，此处只做反查。"""
    for name, value in SOURCE_KINDS.items():
        if value == kind:
            return name
    raise A2VError(f"未知的文章归属类型: {kind}")  # pragma: no cover - 类型已收敛


def for_page(page: str | Path) -> ArticlePaths:
    """以动画网页确定文章归属（渲染与预览走这条路）。

    本地网页必须存在且位于规范目录内；远程网页无法确定归属，直接报错。
    """
    text = str(page)
    if text.startswith(("http://", "https://")):
        raise A2VError(
            f"无法为远程网页 {text} 推导输出路径，请显式指定输出路径"
        )
    page_file = Path(text)
    if page_file.is_dir():
        raise A2VError(f"--page 需要指向网页文件，而不是目录: {page_file}")
    if not page_file.is_file():
        raise A2VError(f"动画网页不存在: {page_file}")
    root = project_root(page_file)
    return article_paths(root, page_file)


def for_storyboard(storyboard: str | Path) -> ArticlePaths:
    """以分镜确定文章归属（配音准备走这条路）。"""
    source = Path(storyboard)
    if not source.is_file():
        raise A2VError(f"分镜脚本不存在: {source}")
    root = project_root(source)
    return article_paths(root, source)


def declares_narration(model: sb.Storyboard) -> bool:
    """分镜是否声明了任何一段口播。

    只用于选择产物文件名与提示，不会自动触发联网配音：有声渲染仍须显式
    传入 `--media`。
    """
    return any((scene.narration or "").strip() for scene in model.scenes)


def use_voiced_name(declares_voice: bool, with_media: bool) -> bool:
    """决定本次导出是否使用配音成片文件名。

    音轨与画面必须同名同源，因此文件名只依据「是否提供媒体」：
    - 提供 `--media` → `voiced.mp4`（+ 同名 SRT）；
    - 未提供 → `silent.mp4`。

    分镜声明了口播却按无声导出时不改名，而是给出警告，避免把带口播的分镜
    静默导出成看似有声的文件。
    """
    if with_media:
        return True
    if declares_voice:
        logger.warning(
            "分镜声明了 narration，但未提供 --media，本次按无声导出为 %s；"
            "需要配音请先执行 prepare.py 再传入 --media",
            SILENT_NAME,
        )
    return False
