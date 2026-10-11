"""文章归属推导与标准输出路径。

文章是**内容**，仓库是**工具链**，两者可以分开放，因此这里区分两层根：

```text
仓库根 repo_root        # .agents/skills/material2video/SKILL.md 所在处：脚本、共享资产、examples
工作区根 workspace_root # 存放 videos|examples/<slug> 与作品产物的目录

<workspace>/videos/<slug>/{article.md, storyboard.json, index.html}
<workspace>/examples/<slug>/...          # 与 videos/ 同构的示例（仓库自带，随仓库分发）
<workspace>/videos/<slug>/outputs/{silent,voiced}.mp4, voiced.srt, media/, previews/
<workspace>/videos/examples/<slug>/outputs/...  # 示例产物独立一层
```

工作区根按 `--content-root` > `M2V_CONTENT_ROOT` > 仓库根 解析：不设内容根时两层根重合，
既有调用方式与画面逐帧不变；设了内容根，文章与产物就可以留在仓库之外。
仓库根内规范目录（`videos|examples/<slug>`）里的输入文件始终按仓库根判定，
以免示例的归属随内容根配置漂移。

本模块集中实现推导规则，命令行只做参数默认值与报错，不再各自拼路径。
所有推导都从输入文件的位置向上查找，与执行命令时的工作目录无关。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from m2v.core.errors import M2VError
from m2v.types.article.media import V4Storyboard

logger = logging.getLogger(__name__)

# 仓库根标记：skill 主文档的位置。它同时是「这个目录属于 material2video 仓库」的证据。
PROJECT_MARKER = Path(".agents/skills/material2video/SKILL.md")

# 源文件的两种归属目录，直接挂在工作区根下。
SOURCE_KINDS: dict[str, str] = {"videos": "article", "examples": "example"}

# 作品目录下的产物目录名（已被 .gitignore 忽略）。
OUTPUTS_DIR = "outputs"

# 成片文件名固定，同类重复导出即覆盖同一个文件。
SILENT_NAME = "silent.mp4"
VOICED_NAME = "voiced.mp4"
PREVIEW_DIR = "previews"
MEDIA_DIR = "media"

#: 内容根环境变量：让文章与产物留在仓库之外的目录里。
#: 命令行参数 `--content-root` 优先于它，两者都没有时工作区根就是仓库根。
CONTENT_ROOT_ENV = "M2V_CONTENT_ROOT"

#: 运行中的 skill bundle 位置：`<仓库根>/.agents/skills/material2video`
from m2v.core.assets import BUNDLE_DIR

ArticleKind = Literal["article", "example"]


@dataclass(frozen=True)
class ArticlePaths:
    """一篇文章的源目录与产物目录。

    字段都是绝对路径；`output_dir` 只表示位置，不保证已经存在。
    """

    repo_root: Path
    workspace_root: Path
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
    """从文件或目录位置向上查找仓库根目录。

    以 `.agents/skills/material2video/SKILL.md` 为标记，而不是 `.git`：
    标记文件兼作「此处是 material2video 仓库根」的判据，避免把任意 Git 仓库
    的顶层目录误认为仓库根。找不到时抛出 M2VError，由调用方补充上下文。
    """
    candidate = Path(path)
    if candidate.is_file():
        candidate = candidate.parent
    try:
        start = candidate.resolve()
    except OSError as exc:  # 路径不可解析时不猜测，交给调用方报错
        raise M2VError(f"无法解析路径 {candidate}: {exc}") from exc
    for directory in (start, *start.parents):
        if (directory / PROJECT_MARKER).is_file():
            return directory
    raise M2VError(
        f"未找到仓库根目录：{start} 及其上级都没有 {PROJECT_MARKER.as_posix()}，"
        f"无法推导文章归属，请显式指定输出路径，或用 --content-root / "
        f"环境变量 {CONTENT_ROOT_ENV} 指定内容根"
    )


def bundle_repo_root() -> Path | None:
    """正在运行的 skill bundle 所在的仓库根。

    文章落在仓库之外时，从输入文件向上是找不到标记的；而「哪份共享资产会被
    挂载、哪份共享页面会被使用」由正在运行的脚本决定，因此这时仓库根取脚本
    自身的位置。bundle 不在仓库里（被拷出去单独使用）时返回 None。
    """
    candidate = BUNDLE_DIR.parents[2]
    return candidate if (candidate / PROJECT_MARKER).is_file() else None


def repo_root_for(path: str | Path) -> Path:
    """输入文件该归到哪个仓库根。

    文件在仓库里时按标记向上找（这就是它所属的仓库）；找不到标记说明文章在
    仓库之外，此时回退到运行中的 bundle 所在仓库——共享资产与共享页面都从
    那里取，挂载的也是那一份。
    """
    try:
        return project_root(path)
    except M2VError:
        bundle = bundle_repo_root()
        if bundle is None:
            raise
        return bundle


def content_root(explicit: str | Path | None = None) -> Path | None:
    """解析内容根：`--content-root` 优先于环境变量 `M2V_CONTENT_ROOT`。

    两者都没有时返回 None，表示「工作区根就是仓库根」——这与引入内容根之前
    的行为完全一致，既有调用方式不需要改。相对路径按当前工作目录解析，
    与其他命令行参数的口径一致。
    """
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    from_env = os.environ.get(CONTENT_ROOT_ENV, "").strip()
    if from_env:
        return Path(from_env).expanduser().resolve()
    return None


def locate_article(root: str | Path, path: str | Path) -> tuple[ArticleKind, str]:
    """判定 `path` 属于工作区根下的哪个文章目录，返回 (类型, slug)。

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
        raise M2VError(f"无法解析路径 {start}: {exc}") from exc

    for directory in (current, *current.parents):
        # 文章目录是 slug 那一层，相对 root 恰好两段：<videos|examples>/<slug>。
        # 因此判据是「父目录名属于 videos/examples，且 slug 目录直接挂在 root 下」，
        # 而不是「这个目录本身叫 videos/examples」。
        kind = SOURCE_KINDS.get(directory.parent.name)
        if kind is not None and _depth_under(root, directory) == 2:
            return kind, directory.name  # type: ignore[return-value]

    raise M2VError(
        f"无法推导文章归属：{start} 不是工作区根 {root} 下的 videos/<slug>/ 或 examples/<slug>/，"
        "请使用规范目录或显式指定输出路径"
    )


def _depth_under(root: Path, directory: Path) -> int:
    """directory 相对 root 的层级数；不在 root 之下时返回 -1。"""
    try:
        return len(directory.relative_to(root).parts)
    except ValueError:
        return -1


def _belongs_to(root: Path, path: str | Path) -> bool:
    """`path` 是否属于 `root` 这个工作区根下的某篇文章（不抛错的 locate）。"""
    try:
        locate_article(root, path)
    except M2VError:
        return False
    return True


def workspace_root_for(
    repo_root: str | Path, path: str | Path, explicit: str | Path | None = None
) -> Path:
    """输入文件该归到哪个工作区根。

    仓库根内规范目录里的输入文件始终按仓库根判定（示例与仓库内文章的行为
    因此不随内容根配置漂移）；其余输入文件必须落在内容根内，否则报错并
    说明两条设置方式，而不是猜一个位置。
    """
    repo = Path(repo_root).resolve()
    if _belongs_to(repo, path):
        return repo
    external = content_root(explicit)
    if external is not None and _belongs_to(external, path):
        return external
    raise M2VError(
        f"无法推导文章归属：{_start_of(path)} 既不在仓库根 {repo} 的 "
        "videos/<slug>/ 或 examples/<slug>/ 内，"
        + (
            f"也不在内容根 {external} 的同构目录内。"
            if external is not None
            else "也没有可用的内容根。"
        )
        + f"内容根用 --content-root 或环境变量 {CONTENT_ROOT_ENV} 指定，"
        "指向存放 videos/<slug>/ 与其 outputs/ 子目录的目录"
    )


def _start_of(path: str | Path) -> Path:
    """报错里要显示的起点：文件取所在目录，目录取自身。"""
    candidate = Path(path)
    return candidate if candidate.is_dir() else candidate.parent


def article_paths(
    repo_root: str | Path, path: str | Path, content_root: str | Path | None = None
) -> ArticlePaths:
    """组合出文章的源目录与产物目录。"""
    repo = Path(repo_root).resolve()
    workspace = workspace_root_for(repo, path, content_root)
    kind, slug = locate_article(workspace, path)
    if kind == "example":
        # 示例源文件仍兼容 examples/<slug>/，但产物统一放到 videos/examples 下，
        # 与正式作品的 videos/<slug>/outputs 结构保持一致且避免同名覆盖。
        output_dir = workspace / "videos" / "examples" / slug / OUTPUTS_DIR
    else:
        output_dir = workspace / "videos" / slug / OUTPUTS_DIR
    return ArticlePaths(
        repo_root=repo,
        workspace_root=workspace,
        kind=kind,
        source_dir=workspace / source_dir_name(kind) / slug,
        output_dir=output_dir,
    )


def source_dir_name(kind: ArticleKind) -> str:
    """归属类型对应的源目录名。SOURCE_KINDS 是唯一权威定义，此处只做反查。"""
    for name, value in SOURCE_KINDS.items():
        if value == kind:
            return name
    raise M2VError(f"未知的文章归属类型: {kind}")  # pragma: no cover - 类型已收敛


def for_page(page: str | Path, content_root: str | Path | None = None) -> ArticlePaths:
    """以一个页面文件确定文章归属（用于推导静态服务根）。

    本地页面必须存在且位于规范目录内；远程地址无法确定归属，直接报错。
    """
    text = str(page)
    if text.startswith(("http://", "https://")):
        raise M2VError(
            f"无法为远程页面 {text} 推导输出路径，请显式指定输出路径"
        )
    page_file = Path(text)
    if page_file.is_dir():
        raise M2VError(f"需要一个页面文件，而不是目录: {page_file}")
    if not page_file.is_file():
        raise M2VError(f"页面文件不存在: {page_file}")
    repo = repo_root_for(page_file)
    return article_paths(repo, page_file, content_root)


def for_storyboard(
    storyboard: str | Path, content_root: str | Path | None = None
) -> ArticlePaths:
    """以分镜确定文章归属（配音准备走这条路）。"""
    source = Path(storyboard)
    if not source.is_file():
        raise M2VError(f"分镜脚本不存在: {source}")
    repo = repo_root_for(source)
    return article_paths(repo, source, content_root)


def declares_narration(model: V4Storyboard) -> bool:
    """分镜是否声明了任何一段口播。

    只用于选择产物文件名与提示，不会自动触发联网配音：有声渲染仍须显式
    传入 `--media`。
    """
    return bool(getattr(model, "has_narration", False))


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
            "需要配音请先执行 m2v prepare --project <目录>",
            SILENT_NAME,
        )
    return False
