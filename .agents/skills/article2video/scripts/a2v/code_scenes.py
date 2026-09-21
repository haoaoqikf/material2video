"""作品级代码场景：模块标识解析与作品归属校验。

代码场景让每幕可以引用作品目录 ``scenes/`` 下的 TypeScript/React 模块。
分镜里只保存**模块标识**（相对 ``scenes/`` 的路径，不含扩展名），
本模块负责三件事：

1. **标识语法**（纯字符串判断，无 I/O）：拒绝扩展名、盘符、绝对路径、
   反斜杠与 ``..`` 段——路径穿越在字符层面就没有入口；
2. **解析与归属**：把标识解析到当前作品 ``scenes/`` 下的真实文件，
   并复核解析结果（含符号链接）没有逃出该目录；
3. **导出契约**：模块必须默认导出场景组件（共享 ``A2VCodeScene`` 类型），
   用静态文本检查确认，缺失时报出源码行号。

结构校验（renderer 判别联合、互斥字段）在 ``storyboard.validate`` 里完成；
这里只做需要文件系统与作品归属的部分，两者共用同一份 ``Issue`` 语义
（错误路径指向分镜字段，源码问题附带行号）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

# 代码场景所在的作品子目录。这是路径契约：模块只能落在这里。
SCENES_DIRNAME = "scenes"

# 模块标识的合法形态：由 [A-Za-z0-9_-] 段组成、可用 / 分段。
# `.` 完全不出现——扩展名、隐藏文件与 `..` 一起被拒。
_MODULE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$")

# 解析标识时依次尝试的后缀（TSX 优先：场景组件几乎都是 JSX）。
_MODULE_SUFFIXES = (".tsx", ".ts", "/index.tsx", "/index.ts")

# Windows 盘符（C: …）与反斜杠：跨平台写法统一走 POSIX 风格相对路径。
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def validate_module_id(module: Any) -> str | None:
    """检查模块标识语法；合法返回 None，否则返回可定位的错误消息。"""
    if not isinstance(module, str) or not module.strip():
        return "代码场景必须声明 renderer.module（scenes/ 下的模块标识，不含扩展名）"
    if module != module.strip():
        return "模块标识前后不能有空白"
    if module.startswith(("/", "\\")):
        return "模块标识必须是相对路径，不能以 / 或 \\ 开头"
    if _DRIVE_RE.match(module):
        return "模块标识必须是当前作品内的相对路径，不能是盘符绝对路径"
    if "\\" in module:
        return "模块标识使用 / 分段，不接受反斜杠"
    if ".." in module.split("/"):
        return "模块标识不能包含 .. 段：模块只能落在当前作品 scenes/ 内"
    if not _MODULE_ID_RE.match(module):
        return (
            "模块标识只允许字母、数字、_ 与 -（可用 / 分段）："
            f"{module!r} 含扩展名或其他非法字符"
        )
    return None


def scenes_dir(article_source_dir: str | Path) -> Path:
    """当前作品允许存放代码场景的目录。"""
    return Path(article_source_dir) / SCENES_DIRNAME


def resolve_module(article_source_dir: str | Path, module: str) -> Path | None:
    """把模块标识解析到作品目录下的真实文件；不存在时返回 None。

    只做字典序拼接，不做任何 ``..`` 归一化——语法检查已拒绝穿越段，
    这里再落到 ``scenes/`` 之下是冗余防线而不是唯一防线。
    """
    base = scenes_dir(article_source_dir)
    for suffix in _MODULE_SUFFIXES:
        candidate = base / f"{module}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def check_export(path: Path) -> tuple[int, str] | None:
    """静态检查模块是否默认导出场景组件。

    返回 ``(行号, 消息)`` 表示失败；通过返回 None。只认文本层面可静态
    判定的两种形态：``export default`` 与 ``export { x as default }``。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return 1, f"代码场景模块读取失败：{exc}"
    if re.search(r"\bexport\s+default\b", text) or re.search(
        r"\bexport\s*\{[^}]*\bas\s+default\b", text
    ):
        return None
    lines = text.splitlines()
    export_line = next(
        (index + 1 for index, line in enumerate(lines) if re.match(r"\s*export\b", line)),
        1,
    )
    if re.search(r"\bexport\b", text):
        return (
            export_line,
            "模块只有具名导出：代码场景必须默认导出场景组件（A2VCodeScene），"
            "例如 `export default function Scene()`",
        )
    return (1, "模块没有任何导出：代码场景必须默认导出场景组件（A2VCodeScene）")


def iter_code_scenes(data: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any], str]]:
    """遍历分镜中声明为 code 的场景，产出 (分镜路径, 场景, 模块标识)。"""
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        return
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        renderer = scene.get("renderer")
        if isinstance(renderer, dict) and renderer.get("kind") == "code":
            module = renderer.get("module")
            yield f"scenes[{index}]", scene, module if isinstance(module, str) else ""


def check(data: dict[str, Any], article_source_dir: str | Path) -> list[tuple[str, str]]:
    """对分镜中的全部代码场景做模块解析与导出检查。

    返回 ``(分镜路径, 消息)`` 列表；消息面向 AI 与人，能直接照着修。
    语法错误已在结构校验报过，这里跳过语法不合法的标识避免重复。
    """
    issues: list[tuple[str, str]] = []
    base = scenes_dir(article_source_dir).resolve()
    for scene_path, _scene, module in iter_code_scenes(data):
        if not module or validate_module_id(module) is not None:
            continue  # 结构校验负责报语法；这里只处理「语法合法但落不了地」的情况
        resolved = resolve_module(article_source_dir, module)
        if resolved is None:
            tried = "、".join(f"{SCENES_DIRNAME}/{module}{suffix or '(目录)'}" for suffix in _MODULE_SUFFIXES)
            issues.append(
                (
                    f"{scene_path}.renderer.module",
                    f"代码场景模块不存在：{module}（尝试过 {tried}）；"
                    f"作品目录：{Path(article_source_dir)}",
                )
            )
            continue
        # 冗余防线：符号链接等方式把文件挪出 scenes/ 时，归属复核拦住它
        try:
            resolved.resolve().relative_to(base)
        except ValueError:
            issues.append(
                (
                    f"{scene_path}.renderer.module",
                    f"代码场景模块必须位于当前作品 {SCENES_DIRNAME}/ 目录内：{module} 解析到了 {resolved}",
                )
            )
            continue
        failed = check_export(resolved)
        if failed is not None:
            line, message = failed
            issues.append(
                (
                    f"{scene_path}.renderer.module",
                    f"{message}（{resolved.name}:{line}）",
                )
            )
    return issues
