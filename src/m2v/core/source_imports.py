"""本地 TS/JS/CSS 引用解析；遍历范围和证据绑定由调用方决定。"""
from __future__ import annotations

import re
from pathlib import Path

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


def import_specifiers(source: str) -> list[str]:
    """返回字面量引用；动态表达式由调用方保守处理。"""
    return [match.group(1) for pattern in _IMPORT_PATTERNS for match in pattern.finditer(source)]


def resolve_import(specifier: str, importer: Path, web: Path) -> Path | None:
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
