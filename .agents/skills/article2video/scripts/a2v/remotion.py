"""Node 侧的逐帧渲染与编码：Python 与 Remotion 之间唯一的边界。

职责划分是刻意的：Python 保留分镜校验、路径归属推导、配音与字幕准备、体检编排、
溯源与交付文件权限修复；Node 只负责**画面执行**——把 React composition 逐帧
渲染并编码成无声 MP4。因此这里只有「起进程、解析它报出来的行、把失败翻译成
能定位的错误」三件事，没有任何判定逻辑。

两边靠 stdout 上**带前缀的行**通信：

- `__A2V_COMPOSITION__{...}`：composition 的真实元数据，渲染前就报出来，
  供渲染入口与分镜交叉校验；
- `__A2V_PROGRESS__<百分比>`：渲染进度。

为什么不用退出码或日志文本猜原因：`remotion` 的日志面向人看，措辞会随版本变化；
把判定挂在日志上，升级一次就会静默失效。
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import assets, code_gate, code_scenes, contract_page, paths, scene_manifest, source_policy
from .browser import PageContract
from .errors import A2VError
from .media import file_digest, fingerprint

logger = logging.getLogger(__name__)

#: Remotion 的入口与 composition 标识。两者都写死在 Python 侧：
#: 它们是渲染契约的一部分，改名会让 `--engine remotion` 找不到画面，
#: 而找不到时的报错必须指向这里而不是让人去猜。
ENTRY_POINT = "src/index.ts"
COMPOSITION_ID = "A2V"

#: 渲染脚本相对 `web/` 的位置
RENDER_SCRIPT = "scripts/remotion-render.mjs"

METADATA_PREFIX = "__A2V_COMPOSITION__"
PROGRESS_PREFIX = "__A2V_PROGRESS__"

#: 依赖安装与打包都按分钟计，逐帧渲染按十分钟计
_BUNDLE_TIMEOUT_S = 600
_METADATA_TIMEOUT_S = 300


class RemotionError(A2VError):
    """Remotion 渲染失败：依赖缺失、打包失败或渲染失败。"""


@dataclass(frozen=True)
class CompositionMetadata:
    """composition 从分镜 props 推导出来的画面参数。"""

    fps: int
    width: int
    height: int
    duration_in_frames: int

    @property
    def contract(self) -> PageContract:
        """当成页面契约用。

        这样 `_resolve_fps` / `_resolve_dimensions` / `_resolve_total_frames`
        三条判定对两条渲染路径完全一致——「画面声明的时长」与「分镜累计的时长」
        必须相等这件事不该因为换了渲染器就换一套写法。
        """
        return PageContract(
            fps=self.fps,
            duration_in_frames=self.duration_in_frames,
            width=self.width,
            height=self.height,
        )


def web_dir() -> Path:
    """前端工程目录（`web/`）。"""
    return contract_page.web_dir()


def program(name: str) -> str:
    """外部程序的**完整路径**。

    不能直接用 `"npx"`：Windows 上 `CreateProcess` 只会自动补 `.exe`，
    而 `npx` 是 `npx.cmd`，于是 `Popen(["npx", …])` 报「系统找不到指定的文件」——
    看起来像没装 Node，实际是调用方式不对。
    """
    found = shutil.which(name)
    if found is None:
        raise RemotionError(
            f"找不到 {name}：Remotion 渲染需要 Node 20 以上版本，"
            f"请安装后重新执行（当前 PATH 里没有 {name}）。"
        )
    return found


def require_environment(web_dir: Path | None = None) -> Path:
    """确认渲染所需的前端依赖与外部程序都在，缺什么就说什么。

    契约页路径下依赖缺失会表现为浏览器里的空白画面或超时，很难反推到
    「没装依赖」；因此这里在起进程之前先查，并把修复命令写在错误里。
    """
    directory = web_dir if web_dir is not None else contract_page.web_dir()
    if not (directory / "package.json").is_file():
        raise RemotionError(
            f"找不到前端工程：{directory / 'package.json'}。请确认仓库完整。"
        )
    if not (directory / "node_modules").is_dir():
        raise RemotionError(
            f"前端依赖未安装：{directory / 'node_modules'} 不存在。"
            f"请先执行 `cd {directory} && pnpm install`。"
        )
    for name in ("npx", "node"):
        program(name)
    return directory


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    what: str,
    on_line: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    """跑一个子进程，把超时与失败翻译成带命令的错误。

    `on_line` 收到每一行输出（stdout 与 stderr 都在内），用于把进度回显给用户；
    失败时的报错里附上输出的最后若干行——Remotion 的失败原因几乎总在最后几行里，
    只报一句「渲染失败」会让人必须重跑一次才能看到原因。
    """
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:  # 可执行文件不存在、权限不足等
        raise RemotionError(f"{what}无法启动：{exc}（命令：{' '.join(command)}）") from exc

    tail: list[str] = []
    assert process.stdout is not None
    try:
        for line in process.stdout:
            stripped = line.rstrip("\n")
            tail.append(stripped)
            if len(tail) > 200:
                del tail[0]
            if on_line is not None:
                on_line(stripped)
            if time.monotonic() - started > timeout_s:
                process.kill()
                raise RemotionError(f"{what}超时（超过 {timeout_s:.0f} 秒）")
        returncode = process.wait()
    finally:
        process.stdout.close()
    if returncode != 0:
        detail = "\n".join(tail[-100:]) or "（没有输出）"
        raise RemotionError(f"{what}失败（退出码 {returncode}）：\n{detail}")
    return subprocess.CompletedProcess(command, returncode, "", "")


def prepare_composition_entry(
    *,
    web_dir: Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
) -> Path:
    """按当前作品重建代码场景静态清单，并检查其归属与安全边界。

    清单在每次 preview / review / render 前整体覆盖：只包含当前作品分镜
    引用的模块，切换作品不会残留上一个作品的引用。分镜声明了代码场景时，
    模块在这里解析归属并确认存在——缺失会在打包/起浏览器之前失败；
    依赖白名单与源码安全闸门也在这里执行，违规即终止，预览与导出都不会开始。

    composition 本身不再由构建期入口选择：契约页与 Remotion 根都按分镜声明的
    契约版本在运行时选择实现，因此「先构建了哪个版本」不再决定这次预览或导出
    能不能渲染当前作品。返回的是本次生成的代码场景清单路径。
    """
    try:
        Path(storyboard_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RemotionError(f"分镜读取失败，无法重建代码场景清单：{exc}") from exc
    manifest = scene_manifest.generate(
        web_dir=web_dir, storyboard_path=storyboard_path, content_root=content_root
    )
    _check_code_scene_boundaries(
        web_dir=web_dir, storyboard_path=Path(storyboard_path), content_root=content_root
    )
    return manifest


def _check_code_scene_boundaries(
    *, web_dir: Path, storyboard_path: Path, content_root: str | Path | None
) -> None:
    """对当前作品的代码场景执行依赖白名单与安全闸门。

    只有分镜声明了代码场景时才解析归属；违规一次性全部列出，
    让 AI 一次修完而不是改一个撞一个。
    """
    try:
        data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RemotionError(f"分镜读取失败，无法检查代码场景边界：{exc}") from exc
    if not any(True for _ in code_scenes.iter_code_scenes(data)):
        return
    article = paths.for_storyboard(storyboard_path, content_root)
    violations = code_gate.check_storyboard(
        article_dir=article.source_dir, storyboard_data=data
    )
    if violations:
        detail = "\n".join(v.render(web_dir) for v in violations)
        raise RemotionError(f"代码场景违反依赖白名单或安全边界：\n{detail}")


def bundle(
    *,
    web_dir: Path,
    out_dir: Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
    timeout_s: float = _BUNDLE_TIMEOUT_S,
) -> Path:
    """把 composition 打包成静态产物，交给后续的取元数据与渲染复用。

    走 CLI 而不是 `@remotion/bundler` 的 `bundle()`：CLI 会读 `remotion.config.ts`，
    因此 `@/` 别名与 Tailwind 只在一处配置。程序化打包不会读那个配置，
    两条路径各配一遍迟早会漂移，而漂移的表现是「Studio 里对、渲染出来错」。

    每次渲染用一个**新的**打包目录：复用固定目录会在源码改动后渲出旧画面，
    而这种错误没有任何症状——成片看起来正常，只是它是上一版。
    """
    prepare_composition_entry(web_dir=web_dir, storyboard_path=storyboard_path, content_root=content_root)
    violations = source_policy.scan(build_inputs())
    if violations:
        detail = "\n".join(item.render(web_dir) for item in violations)
        raise RemotionError(f"composition 源码违反确定性约束：\n{detail}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [program("npx"), "remotion", "bundle", ENTRY_POINT, "--out-dir", str(out_dir)],
        cwd=web_dir,
        timeout_s=timeout_s,
        what="打包 composition",
    )
    if not out_dir.is_dir():
        raise RemotionError(f"打包 composition 后没有产物目录：{out_dir}")
    return out_dir


def metadata(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str = COMPOSITION_ID,
    timeout_s: float = _METADATA_TIMEOUT_S,
) -> CompositionMetadata:
    """读出 composition 由分镜 props 推导出的画面参数。"""
    lines: list[str] = []
    _run(
        [
            program("node"),
            RENDER_SCRIPT,
            "--bundle",
            str(bundle_dir),
            "--props",
            str(props),
            "--composition-id",
            composition_id,
            "--metadata-only",
        ],
        cwd=web_dir,
        timeout_s=timeout_s,
        what="读取 composition 元数据",
        on_line=lines.append,
    )
    payload = _metadata_from(lines)
    if payload is None:
        raise RemotionError(
            f"渲染脚本没有报出 composition 元数据（应有一行以 {METADATA_PREFIX} 开头）。"
            f"输出：\n" + "\n".join(lines[-10:])
        )
    if payload.get("id") != composition_id:
        raise RemotionError(
            f"渲染脚本选中的 composition 是 {payload.get('id')!r}，期望 {composition_id!r}"
        )
    return CompositionMetadata(
        fps=int(payload["fps"]),
        width=int(payload["width"]),
        height=int(payload["height"]),
        duration_in_frames=int(payload["durationInFrames"]),
    )


def render_frames(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    out: Path,
    total_frames: int,
    crf: int,
    preset: str,
    timeout_s: float,
    frame_start: int = 0,
    scale: float = 1,
    composition_id: str = COMPOSITION_ID,
) -> None:
    """把 composition 渲染并编码成无声 MP4。

    音频不在这里合成：配音与字幕的合成、成片验收与交付权限都留在 Python 侧，
    与旧路径共用同一段代码，因此两条路径的成片参数不会各走一套。
    """
    progress_state = {"last": -10}

    def report(line: str) -> None:
        if not line.startswith(PROGRESS_PREFIX):
            return
        percent = _safe_int(line[len(PROGRESS_PREFIX) :])
        if percent is None or percent < progress_state["last"] + 10:
            return
        progress_state["last"] = percent
        logger.info(
            "渲染进度 %d%%（约 %d/%d 帧）", percent, total_frames * percent // 100, total_frames
        )

    command = [
        program("node"),
        RENDER_SCRIPT,
        "--bundle",
        str(bundle_dir),
        "--props",
        str(props),
        "--composition-id",
        composition_id,
        "--out",
        str(out),
        "--crf",
        str(crf),
        "--preset",
        preset,
        # 显式给出帧区间：composition 自己也有时长，但**渲染的帧数**是验收项，
        # 让它由 Python 算出来并在命令行上写死，比隐含在画面里可核对
        "--frames",
        f"{frame_start}-{frame_start + total_frames - 1}",
        "--scale",
        str(scale),
    ]
    _run(
        command,
        cwd=web_dir,
        timeout_s=timeout_s,
        what=f"渲染 {total_frames} 帧",
        on_line=report,
    )
    if not out.is_file() or out.stat().st_size == 0:
        raise RemotionError(f"渲染完成后没有产出文件：{out}")


def _metadata_from(lines: list[str]) -> dict | None:
    """从输出里取元数据行。

    取**最后**一条：打包器与 Remotion 自己的日志都可能出现在前面，
    而元数据是脚本在渲染前打印的，重放时最后一条才是本次的。
    """
    found: dict | None = None
    for line in lines:
        if not line.startswith(METADATA_PREFIX):
            continue
        try:
            found = json.loads(line[len(METADATA_PREFIX) :])
        except json.JSONDecodeError as exc:
            raise RemotionError(f"composition 元数据不是合法 JSON：{line!r}（{exc}）") from exc
    return found


def _safe_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


#: 指纹的起点。三个文件都不是被 import 进来的，必须显式给出：
#: composition 入口、渲染脚本（编码参数由它决定）、打包配置（别名与 Tailwind 在这里）。
_ENTRY_ROOTS = (
    "src/index.ts",
    "scripts/remotion-render.mjs",
    "remotion.config.ts",
)

#: 依赖清单：裸模块的内容不在仓库里，但**版本**由这两份文件锁定
_PACKAGE_FILES = ("package.json", "pnpm-lock.yaml")

#: 引用写法。只认「会真的把另一个文件拉进构建」的那几种。
_IMPORT_PATTERNS = (
    re.compile(r"""\bfrom\s*['"]([^'"]+)['"]"""),  # import x from 'y' / export … from 'y'
    re.compile(r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)"""),  # 动态 import('y')
    re.compile(r"""^[ \t]*import\s+['"]([^'"]+)['"]""", re.MULTILINE),  # 纯副作用 import 'y'
    re.compile(r"""@import\s+(?:url\()?['"]([^'"]+)['"]"""),  # CSS @import
    re.compile(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)"""),  # CSS url(...)
)

#: 解析引用时依次尝试的后缀（含目录入口）
_RESOLVE_SUFFIXES = ("", ".ts", ".tsx", ".css", ".json", ".mjs", "/index.ts", "/index.tsx")


#: 作品文件的指纹键前缀：读自场景清单的 workspaceRoot，让外部内容根的
#: 作品文件也有**可复核**的键（而不是退化成只剩文件名）。
WORK_MOUNT_PREFIX = "__a2v_workspace__"

_MANIFEST_PATH = Path(".gen/scene-manifest.json")


def _manifest_data(repo_root: Path | None = None) -> dict | None:
    """读当前作品的场景清单；没有或损坏时返回 None。"""
    manifest_path = contract_page.web_dir(repo_root) / _MANIFEST_PATH
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def fingerprint_mounts(repo_root: Path | None = None, workspace_root: str | Path | None = None) -> dict[str, Path]:
    """指纹键使用的挂载表：与契约页服务器同一套别名。

    构建输入全在 `web/` 下，而工作区根可能是仓库之外的内容根——那时
    `asset_key` 会退化成只记文件名，复核时拼不回去、每一份成片都被判成
    「资产不见了」。挂上 `web/` 的别名之后，键与工作区根在哪无关；
    作品文件再挂 `__a2v_workspace__`（根读自场景清单），记录与复核
    两侧走同一份清单，键永远能拼回真实文件。
    """
    mounts = {**assets.default_mounts(), **contract_page.web_mounts(repo_root)}
    data = _manifest_data(repo_root)
    workspace = str(workspace_root) if workspace_root is not None else (data.get("workspaceRoot") if data else None)
    if workspace:
        mounts[WORK_MOUNT_PREFIX] = Path(str(workspace))
    return mounts


def _imports_of(path: Path) -> list[str]:
    """文件里引用的其它文件（原样，不解析）。"""
    if path.suffix.lower() not in (".ts", ".tsx", ".mjs", ".css"):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    found: list[str] = []
    for pattern in _IMPORT_PATTERNS:
        found.extend(match.group(1) for match in pattern.finditer(text))
    return found


def _resolve_import(specifier: str, importer: Path, web: Path) -> Path | None:
    """引用 → 仓库里的文件；裸模块与取不到的引用返回 None。"""
    if Path(specifier).is_absolute():
        base = Path(specifier)
    elif specifier.startswith(("@/", "~/")):
        base = web / "src" / specifier[2:]
    elif specifier.startswith("."):
        base = importer.parent / specifier
    else:
        # 裸模块（react、remotion、dagre…）：内容在 node_modules 里，
        # 由 package.json 与锁文件锁定版本，不逐个指纹
        return None
    for suffix in _RESOLVE_SUFFIXES:
        candidate = Path(f"{base}{suffix}")
        if candidate.is_file():
            return candidate
    return None


def _storyboard_modules(storyboard_path: str | Path, content_root: str | Path | None = None) -> list[Path]:
    """解析当前分镜真正引用的代码场景源文件，避免依赖全局生成清单的最后写入者。"""
    data = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    article = paths.for_storyboard(storyboard_path, content_root)
    found: dict[Path, None] = {}
    for _scene_path, _scene, module in code_scenes.iter_code_scenes(data):
        if module:
            resolved = code_scenes.resolve_module(article.source_dir, module)
            if resolved is not None:
                found[resolved.resolve()] = None
    return list(found)


def _manifest_modules(repo_root: Path | None = None) -> list[Path]:
    data = _manifest_data(repo_root)
    result: dict[Path, None] = {}
    for item in (data or {}).get("modules", []):
        raw = item.get("module") if isinstance(item, dict) else None
        if raw and Path(raw).is_file():
            result[Path(raw).resolve()] = None
    return list(result)


def build_inputs(
    repo_root: Path | None = None,
    *,
    storyboard_path: str | Path | None = None,
    content_root: str | Path | None = None,
) -> list[Path]:
    """画面与编码的全部构建输入：从入口出发**沿引用可达**的文件。

    刻意不做「扫描整个 `src/`」：那样改一个没有任何画面用到的文件也会让所有
    成片判成「落后」，闸门立刻沦为噪音，而人一旦开始忽略它，它就不再是闸门。
    反面同样要防：可达性算少了会让「改了组件却判成当前」——所以入口、字体、
    依赖清单这些不被 import 的东西必须显式列出来。
    """
    web = contract_page.web_dir(repo_root)
    seen: dict[Path, None] = {}

    queue = [candidate for name in _ENTRY_ROOTS if (candidate := web / name).is_file()]
    queue.extend(_storyboard_modules(storyboard_path, content_root) if storyboard_path else _manifest_modules(repo_root))
    generated_indexes = {
        (web / scene_manifest.GENERATED_MANIFEST).resolve(),
        (web / ".gen" / "active-tailwind.css").resolve(),
    }
    while queue:
        resolved = queue.pop().resolve()
        # 全局生成索引与 active-tailwind.css 都是从当前作品派生的临时文件，
        # 不同作品构建时会互相覆盖。真正的代码场景源文件与其导入会按分镜进入 queue。
        if resolved in generated_indexes:
            continue
        if resolved in seen:
            continue
        seen[resolved] = None
        for specifier in _imports_of(resolved):
            target = _resolve_import(specifier, resolved, web)
            if target is not None:
                queue.append(target)

    for name in _PACKAGE_FILES:
        candidate = web / name
        if candidate.is_file():
            seen[candidate.resolve()] = None
    # 字体取**源文件**而不是 `public/fonts/` 里的构建副本：副本是派生物，
    # 没构建过就不存在，那会让每一次复核都报「不见了」
    for font in contract_page.font_files(repo_root):
        seen[font.resolve()] = None
    return sorted(seen)


def build_input_fingerprint(
    repo_root: Path | None = None,
    *,
    storyboard_path: str | Path | None = None,
    content_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> dict:
    """成片溯源用的构建输入指纹。

    口径与页面路径一致（同样是 `{"files": {...}, "digest": ...}`），
    因此 `provenance_status` 的复核逻辑两条路径共用一套。
    """
    mounts = fingerprint_mounts(repo_root, workspace_root)
    root = contract_page.web_dir(repo_root)
    files = {
        assets.asset_key(path, root, mounts): file_digest(path)
        for path in build_inputs(repo_root, storyboard_path=storyboard_path, content_root=content_root)
    }
    ordered = dict(sorted(files.items()))
    return {"files": ordered, "digest": fingerprint(ordered)}
