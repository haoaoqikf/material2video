"""React composition 的确定性源码闸门。"""

from __future__ import annotations

import json
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
_CSS_MOTION = re.compile(r"(?:^|[;{\s])(?:animation(?:-[\w-]+)?|transition(?:-[\w-]+)?)\s*:|@keyframes\b", re.MULTILINE)


def load_catalog(web: Path) -> list[dict]:
    path = web / "src/third-party/catalog.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def scan(web: Path, build_inputs: list[Path]) -> list[Violation]:
    """扫描 composition 可达源码和分类表中实际接入的第三方源码。"""
    catalog = load_catalog(web)
    allowed_css: set[Path] = set()
    extra: set[Path] = set()
    for item in catalog:
        if item.get("status") != "representative":
            continue
        for key in ("source", "styles"):
            value = item.get(key)
            if value:
                path = (web / value).resolve()
                extra.add(path)
                if key == "styles" and item.get("classification") == "css-keyframes":
                    allowed_css.add(path)

    violations: list[Violation] = []
    for path in sorted({p.resolve() for p in build_inputs} | extra):
        if path.suffix.lower() not in {".ts", ".tsx", ".css", ".mjs"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for rule, pattern in _RULES:
            for match in pattern.finditer(text):
                violations.append(_violation(path, text, match.start(), rule))
        if path not in allowed_css:
            for match in _CSS_MOTION.finditer(text):
                violations.append(_violation(path, text, match.start(), "未适配的 CSS 动画/过渡"))

    # 允许 CSS keyframes 的唯一前提不是目录名，而是组件确实经过统一包装层。
    for item in catalog:
        if item.get("status") == "representative" and item.get("classification") == "css-keyframes":
            source = web / str(item.get("source", ""))
            content = source.read_text(encoding="utf-8", errors="replace") if source.is_file() else ""
            if "FrameSyncedCssAnimation" not in content:
                violations.append(Violation(source, 1, "CSS 动画未经过帧同步包装", item.get("id", "未知组件")))
    return violations


def _violation(path: Path, text: str, offset: int, rule: str) -> Violation:
    line = text.count("\n", 0, offset) + 1
    excerpt = text.splitlines()[line - 1] if text.splitlines() else ""
    return Violation(path, line, rule, excerpt)
