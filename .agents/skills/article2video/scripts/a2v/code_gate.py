"""作品级代码场景的依赖白名单与源码安全闸门。

两层检查，都从**每个代码场景入口遍历完整可达导入图**——只扫入口文件
挡不住辅助模块绕行，传递依赖同样受检：

1. **依赖白名单**（任务 3.1）：裸模块只允许固定集合（React、React DOM、
   Remotion、ECharts、Dagre、Lucide、项目公开 API ``@a2v/scene``）；
   Node 内置模块、``require`` 与动态 ``import()`` 一律拒绝；相对导入必须
   留在当前作品的 ``scenes/`` 与 ``assets/`` 内。
2. **确定性/安全静态扫描**（任务 3.2）：按规则编号拒绝动态代码求值、
   进程/文件系统、网络 API、外部 URL、挂钟、系统随机、计时器、动画循环
   与 CSS 时间动画，诊断带文件、行列与规则编号。

这不是恶意代码沙箱：它面向本地、受审查的 AI 生成作品源码，
配合运行期断网（offline guard + 浏览器路由阻断）构成两层边界。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import code_scenes

# ---------------------------------------------------------------------------
# 白名单
# ---------------------------------------------------------------------------

#: 允许的裸模块根。与 web/package.json 的依赖一致；新增任何包都是
#: 独立行为变更，不由作品按需引入。
ALLOWED_BARE_ROOTS = frozenset(
    {
        "react",
        "react-dom",
        "remotion",
        "echarts",
        "@dagrejs/dagre",
        "lucide-react",
        "@a2v/scene",  # 项目公开的代码场景 API（tsconfig/vite/webpack 三处别名同一指向）
    }
)

#: 允许的前缀型裸模块（项目实际用到的 Remotion 子包）。
ALLOWED_BARE_PREFIXES = ("@remotion/",)

#: Node 内置模块清单（常见集合 + node: 前缀一律拒绝）。
NODE_BUILTIN_ROOTS = frozenset(
    {
        "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
        "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
        "events", "fs", "http", "http2", "https", "inspector", "module", "net",
        "os", "path", "perf_hooks", "process", "punycode", "querystring",
        "readline", "repl", "stream", "string_decoder", "sys", "timers", "tls",
        "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads",
        "zlib",
    }
)


def bare_root(specifier: str) -> str:
    """取裸模块的包根：``react/jsx-runtime`` → ``react``，作用域包取两段。"""
    if specifier.startswith("@"):
        return "/".join(specifier.split("/")[:2])
    return specifier.split("/")[0]


# ---------------------------------------------------------------------------
# 诊断
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """一条闸门违规：作品相对路径、行列与规则编号，直接可定位。"""

    path: Path
    line: int
    column: int
    rule: str
    message: str

    def render(self, root: Path) -> str:
        try:
            name = self.path.relative_to(root)
        except ValueError:
            name = self.path
        return f"{name.as_posix()}:{self.line}:{self.column}: [{self.rule}] {self.message}"


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    column = offset - (text.rfind("\n", 0, offset) + 1) + 1
    return line, column


# ---------------------------------------------------------------------------
# 静态规则（任务 3.2）：规则编号 A5–A15，A1–A4 由导入图检查给出
# ---------------------------------------------------------------------------

_SCRIPT_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "A5 动态代码求值",
        re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(|\bFunction\s*\(\s*['\"]"),
        "动态求值让画面不可静态分析；把计算写成普通 TypeScript 表达式",
    ),
    (
        "A6 进程/文件系统",
        re.compile(r"\bprocess\s*\.(?:env|exit|cwd|argv|kill|hrtime)\b|__dirname|__filename|require\.resolve"),
        "作品代码运行在浏览器里，不接触进程与文件系统",
    ),
    (
        "A7 网络 API",
        re.compile(r"\bfetch\s*\(|new\s+XMLHttpRequest\s*\(|new\s+WebSocket\s*\(|new\s+EventSource\s*\(|\bnavigator\.sendBeacon\s*\("),
        "画面离线可渲染：任何网络请求都不允许；数据必须来自分镜或本地资产",
    ),
    (
        "A9 挂钟",
        re.compile(r"\bDate\.now\s*\(|\bperformance\.now\s*\(|\bnew\s+Date\s*\(\s*\)"),
        "可见状态只能是帧号的函数；用注入的 frame/progress 表达时间",
    ),
    (
        "A10 系统随机",
        re.compile(r"\bMath\.random\s*\(\s*\)|getRandomValues\s*\("),
        "系统随机不可复现；使用 @a2v/scene 的稳定种子 random()",
    ),
    (
        "A11 计时器",
        re.compile(r"\b(?:setTimeout|setInterval|setImmediate|queueMicrotask)\s*\("),
        "计时器与逐帧渲染冲突；用帧号驱动状态变化",
    ),
    (
        "A12 动画循环",
        re.compile(r"\brequestAnimationFrame\s*\(|\brequestIdleCallback\s*\("),
        "动画循环由 Remotion 驱动；组件只按当前帧求值",
    ),
    (
        "A15 自建 composition",
        re.compile(r"\bregisterRoot\s*\(|<Composition[\s>/]"),
        "作品不得注册 Remotion 根或声明独立 composition；画面由共享 composition 承载",
    ),
)

#: CSS 时间动画在样式文件与 TSX 内联样式字符串里都可能出现。
_CSS_MOTION_RULE = (
    "A13 CSS 时间动画",
    re.compile(r"(?:^|[;{(\s])(?:animation(?:-[\w-]+)?|transition(?:-[\w-]+)?)\s*:|@keyframes\b", re.MULTILINE),
    "CSS 动画/过渡按真实时间推进，与帧号无关；用帧号计算样式值",
)
#: 外链 URL（源码字符串与 CSS url()），含协议相对写法 //host。
_EXTERNAL_URL_RULE = (
    "A8 外部 URL",
    re.compile(r"""['"`]https?://[^'"`\s]*['"`]|url\(\s*['"]?(?:https?:)?//|['"`](?:https?:)?//[\w.-]+""", re.MULTILINE),
    "外部 URL 让画面依赖网络与第三方状态；资产必须本地化",
)

#: 扫描的文件后缀：代码 + 样式 + SVG。
_SCANNED_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".css", ".svg"}
#: 导入图会走入的文本后缀（其余后缀只做存在性归属检查）。
_WALKED_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".css"}

#: 静态 import 的两种形式：`from '...'` 与副作用 `import '...'`。
_STATIC_IMPORT_RE = re.compile(
    r"""\bfrom\s*['\"](?P<from>[^'\"]+)['\"]"""
    r"""|^[ \t]*import\s*['\"](?P<side>[^'\"]+)['\"]""",
    re.MULTILINE,
)
#: 动态模块加载（动态 import 与 require，含非字面量形式）。
_DYNAMIC_IMPORT_RE = re.compile(r"\bimport\s*\(|\brequire\s*\(|\brequire\.resolve\b")
#: CSS 引入与资源引用。
_CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\(\s*)?['\"]?([^'\"\);]+)""", re.IGNORECASE)
_CSS_URL_RE = re.compile(r"""url\(\s*['\"]?([^'\")]+)['\"]?\s*\)""", re.IGNORECASE)
#: SVG 逃生口：脚本、事件属性与外部 <use>。
_SVG_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "A14 SVG 脚本/事件/外部引用",
        re.compile(
            r"<script[\s>]|javascript:|on[a-z]+\s*=|<(?:use|image)[^>]*?(?:xlink:)?href\s*=\s*[\"'](?!#)",
            re.IGNORECASE,
        ),
        "SVG 只作为静态图形使用：不接受脚本、事件与外部文件引用",
    ),
)


# ---------------------------------------------------------------------------
# 导入图
# ---------------------------------------------------------------------------

#: 相对导入解析时依次尝试的后缀。
_RESOLVE_SUFFIXES = ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".css", ".svg", "/index.ts", "/index.tsx", "/index.js")


def _resolve_relative(specifier: str, importer: Path) -> Path | None:
    base = importer.parent / specifier
    for suffix in _RESOLVE_SUFFIXES:
        candidate = Path(f"{base}{suffix}")
        if candidate.is_file():
            return candidate
    return None


def _within(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    return any(resolved.is_relative_to(root.resolve()) for root in roots)


def _specifier_issues(
    specifier: str, importer: Path, article_dir: Path, offset: int, text: str
) -> list[Violation]:
    """静态导入说明符的归属与白名单判定。"""
    path, line, column = importer, *_line_col(text, offset)
    if specifier.startswith("node:"):
        return [Violation(path, line, column, "A2 Node 内置能力", f"导入 Node 内置模块 {specifier!r}")]
    is_relative = specifier.startswith(("./", "../")) or specifier in (".", "..")
    if not is_relative and not specifier.startswith("/"):
        root = bare_root(specifier)
        if root in NODE_BUILTIN_ROOTS:
            return [Violation(path, line, column, "A2 Node 内置能力", f"导入 Node 内置模块 {root!r}")]
        if root in ALLOWED_BARE_ROOTS or any(root.startswith(prefix) for prefix in ALLOWED_BARE_PREFIXES):
            return []
        if specifier.startswith("@/"):
            return [
                Violation(
                    path,
                    line,
                    column,
                    "A1 非白名单依赖",
                    f"项目内部模块不对作品开放：{specifier!r}；作品只能导入 @a2v/scene",
                )
            ]
        return [
            Violation(
                path,
                line,
                column,
                "A1 非白名单依赖",
                f"包 {root!r} 不在代码场景白名单（允许：react、react-dom、remotion、"
                "@remotion/*、echarts、@dagrejs/dagre、lucide-react、@a2v/scene）",
            )
        ]
    # 相对导入：解析并复核边界（scenes/ 与 assets/）
    resolved = _resolve_relative(specifier, importer)
    if resolved is None:
        return [
            Violation(path, line, column, "A4 越界相对导入", f"相对导入 {specifier!r} 解析不到文件")
        ]
    boundary = [Path(article_dir) / code_scenes.SCENES_DIRNAME, Path(article_dir) / "assets"]
    if not _within(resolved, boundary):
        return [
            Violation(
                path,
                line,
                column,
                "A4 越界相对导入",
                f"相对导入 {specifier!r} 落在作品 scenes/ 与 assets/ 之外：{resolved}",
            )
        ]
    return []


def scan(
    *,
    article_dir: Path,
    modules: list[Path],
    roots: list[Path] | None = None,
) -> list[Violation]:
    """从每个代码场景入口遍历可达导入图并应用全部规则。

    ``modules`` 是入口文件绝对路径清单（scene-manifest 产物）；
    ``roots`` 覆盖默认边界（scenes/ 与 assets/），测试夹具用。
    """
    boundary = roots or [Path(article_dir) / code_scenes.SCENES_DIRNAME, Path(article_dir) / "assets"]
    violations: list[Violation] = []
    seen: dict[Path, None] = {}
    queue = [entry.resolve() for entry in modules if entry.is_file()]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen[current] = None
        try:
            text = current.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            violations.append(Violation(current, 1, 1, "A0 读取失败", str(exc)))
            continue
        violations.extend(_scan_text(current, text))
        if current.suffix.lower() not in _WALKED_SUFFIXES:
            continue
        for specifier, offset in _static_specifiers(current, text):
            for violation in _specifier_issues(specifier, current, Path(article_dir), offset, text):
                violations.append(violation)
            # 继续沿合法的相对导入行走
            if specifier.startswith(("./", "../")):
                resolved = _resolve_relative(specifier, current)
                if resolved is not None and resolved.suffix.lower() in _SCANNED_SUFFIXES:
                    queue.append(resolved.resolve())
    return violations


def _static_specifiers(path: Path, text: str) -> list[tuple[str, int]]:
    """文件里的静态导入说明符（CSS 走 @import/url；其余走 import/from）。"""
    if path.suffix.lower() == ".css":
        found: list[tuple[str, int]] = []
        for pattern in (_CSS_IMPORT_RE, _CSS_URL_RE):
            for match in pattern.finditer(text):
                found.append((match.group(1).strip(), match.start(1)))
        return found
    found = []
    for match in _STATIC_IMPORT_RE.finditer(text):
        if match.group("from") is not None:
            found.append((match.group("from"), match.start("from")))
        elif match.group("side") is not None:
            found.append((match.group("side"), match.start("side")))
    return found


def _scan_text(path: Path, text: str) -> list[Violation]:
    """对单文件文本应用全部规则；相对导入的边界在调用方复核。"""
    violations: list[Violation] = []
    suffix = path.suffix.lower()
    for match in _DYNAMIC_IMPORT_RE.finditer(text):
        line, column = _line_col(text, match.start())
        violations.append(
            Violation(
                path,
                line,
                column,
                "A3 动态模块加载",
                "require 与动态 import() 无法静态分析；改为顶层静态 import",
            )
        )
    rules = list(_SCRIPT_RULES)
    if suffix == ".svg":
        rules.extend(_SVG_RULES)
    else:
        rules.extend((_CSS_MOTION_RULE, _EXTERNAL_URL_RULE))
    for rule, pattern, advice in rules:
        for match in pattern.finditer(text):
            line, column = _line_col(text, match.start())
            violations.append(Violation(path, line, column, rule, advice))
    return violations


# ---------------------------------------------------------------------------
# 编排入口
# ---------------------------------------------------------------------------


def check_storyboard(
    *,
    article_dir: Path,
    storyboard_data: dict,
) -> list[Violation]:
    """按分镜解析代码场景入口并扫描；无代码场景时返回空。"""
    entries: list[Path] = []
    for _scene_path, _scene, module in code_scenes.iter_code_scenes(storyboard_data):
        if not module:
            continue
        resolved = code_scenes.resolve_module(article_dir, module)
        if resolved is not None:
            entries.append(resolved)
    if not entries:
        return []
    return scan(article_dir=Path(article_dir), modules=entries)
