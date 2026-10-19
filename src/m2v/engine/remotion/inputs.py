"""输入指纹与入口常量：从渲染入口出发**沿引用可达**的构建输入。

打包的缓存键、源码确定性扫描与成片溯源都用这里算出来的同一批文件。刻意不做
「扫描整个 `src/`」：那样改一个没有任何画面用到的文件也会让所有成片判成
「落后」，闸门立刻沦为噪音，而人一旦开始忽略它，它就不再是闸门。
"""

from __future__ import annotations

import re
from pathlib import Path

import m2v.core.assets as assets
import m2v.engine.contract_page as contract_page
from m2v.core.fingerprints import file_digest, fingerprint as calculate_fingerprint

#: Remotion 入口。它写死在 Python 侧：是渲染契约的一部分，改名会让打包找不到画面，
#: 而找不到时的报错必须指向这里而不是让人去猜。
ENTRY_POINT = "src/index.ts"

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


#: 外部内容根的显式指纹挂载前缀。
WORK_MOUNT_PREFIX = "__m2v_workspace__"

def fingerprint_mounts(repo_root: Path | None = None, workspace_root: str | Path | None = None) -> dict[str, Path]:
    """指纹键使用的挂载表：与契约页服务器同一套别名。

    构建输入全在 `web/` 下，而工作区根可能是仓库之外的内容根——那时
    `asset_key` 会退化成只记文件名，复核时拼不回去、每一份成片都被判成
    「资产不见了」。挂上 `web/` 的别名之后，键与工作区根在哪无关；
    显式内容根使用 `__m2v_workspace__` 挂载，记录和复核采用相同路径键。
    """
    mounts = {**assets.default_mounts(), **contract_page.web_mounts(repo_root)}
    workspace = workspace_root
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


def build_inputs(repo_root: Path | None = None) -> list[Path]:
    """画面与编码的全部构建输入：从入口出发**沿引用可达**的文件。

    刻意不做「扫描整个 `src/`」：那样改一个没有任何画面用到的文件也会让所有
    成片判成「落后」，闸门立刻沦为噪音，而人一旦开始忽略它，它就不再是闸门。
    反面同样要防：可达性算少了会让「改了组件却判成当前」——所以入口、字体、
    依赖清单这些不被 import 的东西必须显式列出来。

    """
    web = contract_page.web_dir(repo_root)
    seen: dict[Path, None] = {}

    queue = [candidate for name in _ENTRY_ROOTS if (candidate := web / name).is_file()]
    while queue:
        resolved = queue.pop().resolve()
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
        for path in build_inputs(repo_root)
    }
    ordered = dict(sorted(files.items()))
    return {"files": ordered, "digest": calculate_fingerprint(ordered)}


def web_dir() -> Path:
    """前端工程目录（`web/`）。"""
    return contract_page.web_dir()
