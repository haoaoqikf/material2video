"""React composition 的确定性源码闸门。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    rule: str
    excerpt: str

    def render(self, root: Path) -> str:
        try:
            name = self.path.relative_to(root)
        except ValueError:
            name = self.path
        return f"{name}:{self.line}: {self.rule}: {self.excerpt.strip()}"


_RULES = (
    ("挂钟时间", re.compile(r"\b(?:Date\.now|performance\.now)\s*\(")),
    ("随机数", re.compile(r"\bMath\.random\s*\(")),
    ("计时器", re.compile(r"\b(?:setTimeout|setInterval|requestAnimationFrame)\s*\(")),
    ("动画库入口", re.compile(r"(?:from\s*['\"](?:motion(?:/react)?|framer-motion|gsap)['\"]|\buseAnimate\s*\()")),
    ("无限动画工具类", re.compile(r"\banimate-[\w-]+[^\n'\"]*\binfinite\b|\banimate-infinite\b")),
)
#: CSS/样式对象里的时间动效声明。**值为「关闭」形态的放行**：
#: `animation: false`、`transition: none`、`animation-delay: 0` 是
#: 「适配」本身（关掉第三方库的时钟），不是违规——ECharts 适配器
#: 恰恰靠这一行把图表压成帧驱动。判定在 `_is_motion_off` 里做，
#: 不塞进正则：值形态千变万化，负向先行断言漏一处就是假阴性。
_CSS_MOTION = re.compile(
    r"(?:^|[;{\s])(animation(?:-[\w-]+)?|transition(?:-[\w-]+)?)\s*:\s*([^;{}\n]*)|(@keyframes)\b",
    re.MULTILINE,
)

_MOTION_OFF_VALUES = {"false", "undefined", "none", "'none'", '"none"'}


def _is_motion_off(value: str) -> bool:
    """动效声明的值是否为「完全关闭」：时长为零或显式 none/false。"""
    text = value.strip().rstrip(",").strip()
    if text in _MOTION_OFF_VALUES:
        return True
    return re.fullmatch(r"0+(?:\.0+)?(?:s|ms)?", text) is not None


def _scan_text(path: Path, text: str, extra: tuple[tuple[str, re.Pattern], ...] = ()) -> list[Violation]:
    violations: list[Violation] = []
    for rule, pattern in (*_RULES, *extra):
        for match in pattern.finditer(text):
            violations.append(_violation(path, text, match.start(), rule))
    for match in _CSS_MOTION.finditer(text):
        # TypeScript schema 属性名（例如 `transition: transitionSchema.optional()`）
        # 不是 CSS 声明，不能被源码策略误判为浏览器过渡。
        if match.group(2) and ("Schema" in match.group(2) or ".optional(" in match.group(2)):
            continue
        if match.group(3):
            violations.append(_violation(path, text, match.start(), "未适配的 CSS 动画/过渡"))
            continue
        if _is_motion_off(match.group(2) or ""):
            continue
        violations.append(_violation(path, text, match.start(), "未适配的 CSS 动画/过渡"))
    return violations


def scan(build_inputs: list[Path]) -> list[Violation]:
    """扫描 composition 的可达源码。

    共享 composition 及其可达样式只按帧号决定画面，禁止隐式时间和随机源。
    """
    violations: list[Violation] = []
    for path in sorted({p.resolve() for p in build_inputs}):
        if path.suffix.lower() not in {".ts", ".tsx", ".css", ".mjs"} or not path.is_file():
            continue
        violations.extend(_scan_text(path, path.read_text(encoding="utf-8", errors="replace")))
    return violations


#: 纯时间场景额外禁止的写法：它们要么依赖真实时钟，要么由库自走动画。
_PURE_RULES = (
    ("R3F 逐帧回调", re.compile(r"\buseFrame\s*\(")),
    ("ECharts 自走动画", re.compile(r"\b(?:echarts|Chart)\b")),
    ("真实日期", re.compile(r"\bnew\s+Date\s*\(")),
    ("加密随机源", re.compile(r"\bcrypto\.getRandomValues\s*\(")),
    ("元素动画", re.compile(r"\.animate\s*\(")),
    ("媒体自走播放", re.compile(r"\b(?:video|audio)\s*\.\s*play\s*\(")),
    ("空闲回调", re.compile(r"\brequestIdleCallback\s*\(")),
)


def _strip_comments(text: str) -> str:
    """去掉注释但保留行数，避免注释里的示例词把纯场景判成违规。"""
    text = re.sub(r"/\*.*?\*/", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def scan_pure(build_inputs: list[Path]) -> list[Violation]:
    """pure-time 场景的静态闸门：基础禁用项 + 自走动画/真实时钟。"""
    violations: list[Violation] = []
    for path in sorted({p.resolve() for p in build_inputs}):
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css"} or not path.is_file():
            continue
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        violations.extend(_scan_text(path, text, _PURE_RULES))
    return violations


def _violation(path: Path, text: str, offset: int, rule: str) -> Violation:
    line = text.count("\n", 0, offset) + 1
    excerpt = text.splitlines()[line - 1] if text.splitlines() else ""
    return Violation(path, line, rule, excerpt)
