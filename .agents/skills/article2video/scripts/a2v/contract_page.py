"""渲染契约页的定位与 URL 组装。

画面由 React composition 实现，但要被体检与量测驱动，它必须挂在一个**普通网页**里。
那个网页就是契约页：`web/dist/contract/contract.html`。它由 Vite 构建，
内容层（分镜）通过查询参数 `a2v-storyboard` 交给它，因此**一个页面服务任意作品**，
作品不再各自拥有一份 HTML。

这里负责三件事，别处不要重复推导：

1. **它在哪**：由 skill 位置推出仓库根，再拼 `web/dist/contract/contract.html`；
2. **怎么被访问到**：内容根可能落在仓库之外（页面在仓库里、分镜在内容根里），
   因此静态根取工作区根、`web/` 目录走服务器别名挂载；
3. **尚未构建时怎么报错**：报出缺哪个文件、要跑哪条命令。

别名用的是与共享资产同一套挂载机制（`static_server` 的 `mounts`），
因此不会扩大静态根，越界请求照旧 404。
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from . import assets
from .errors import A2VError
from .http_server import LocalServer

#: `web/` 目录的服务器别名前缀。页面在这里，分镜在工作区根里，靠它接起来。
WEB_MOUNT = "/__a2v_web__"

#: 契约页实现的渲染契约版本。
#: **升级时必须同步改这里，并同步 `web/src/contract/bridge.ts`**：
#: 两个版本的 `ready` 与 `seekToFrame` 签名相同、语义不同，版本号是唯一能在
#: 早期把两者分开的信号（旧页面在首帧截图上表现为空白，很难反推原因）。
CONTRACT_VERSION = 2

#: 旧动画网页声明的契约版本。迁移期它仍是默认引擎，因此必须继续被接受；
#: 默认引擎切到契约页之后，这个常量与旧页面一起消失。
LEGACY_CONTRACT_VERSION = 1

#: 契约页相对 `web/` 的位置：Vite 的构建产物
CONTRACT_PAGE_RELATIVE = Path("dist/contract/contract.html")

#: 构建命令：报错信息里要给出可照抄的一条命令
BUILD_HINT = "cd web && pnpm install && pnpm build"


def repository_root() -> Path:
    """仓库根：由本文件位置推出，与仓库放在哪里无关。

    `scripts/a2v/contract_page.py` → `scripts/a2v` → `scripts` → skill → `.agents` → 仓库根。
    """
    return assets.BUNDLE_DIR.parents[2]


def web_dir(repo_root: Path | None = None) -> Path:
    """前端工程目录。"""
    return (repo_root or repository_root()) / "web"


def contract_page_path(repo_root: Path | None = None) -> Path:
    """契约页的构建产物路径。"""
    return web_dir(repo_root) / CONTRACT_PAGE_RELATIVE


def require_contract_page(repo_root: Path | None = None) -> Path:
    """契约页的构建产物，不存在时给出可照抄的构建命令。

    特意不在这里自动构建：构建要动 Node 工具链、耗时以十秒计，
    而且失败原因（依赖没装、网络不通）与渲染失败完全是两回事，
    混在渲染流程里会变成一句看不懂的报错。
    """
    page = contract_page_path(repo_root)
    if not page.is_file():
        raise A2VError(
            f"渲染契约页不存在: {page}\n"
            f"它是画面与渲染入口之间的接口，需要先用 Vite 构建：{BUILD_HINT}"
        )
    return page


def web_mounts(repo_root: Path | None = None) -> dict[str, Path]:
    """契约页所在的挂载表：别名前缀 → `web/` 目录。"""
    directory = web_dir(repo_root)
    if not directory.is_dir():
        raise A2VError(
            f"前端工程目录不存在: {directory}\n"
            f"画面实现与契约页都在它下面，请确认仓库结构完整：{BUILD_HINT}"
        )
    return {WEB_MOUNT: directory}


def mounts_for_contract_page(repo_root: Path | None = None) -> dict[str, Path]:
    """契约页路径上的完整挂载表。

    同时保留 skill 资产别名：迁移期两条渲染路径并存，同一台服务器要能
    同时服务契约页与旧页面，否则体检与渲染会各起一台，端口与生命周期都要重来一遍。
    """
    return {**assets.default_mounts(), **web_mounts(repo_root)}


def storyboard_url(storyboard: str | Path, workspace_root: str | Path) -> str:
    """分镜在静态根下的 URL 路径。

    相对**工作区根**，因为契约页的静态根就是工作区根；分镜在工作区根之外
    属于调用方的路径归属错误，这里直接报错而不是拼出一个取不到的地址。
    """
    resolved = Path(storyboard).resolve()
    root = Path(workspace_root).resolve()
    try:
        return "/" + resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise A2VError(
            f"分镜不在工作区根内，契约页取不到它：分镜 {resolved}，工作区根 {root}"
        ) from exc


def with_storyboard_query(url: str, storyboard_path: str) -> str:
    """给契约页 URL 补上 `a2v-storyboard` 查询参数。"""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}a2v-storyboard={quote(storyboard_path, safe='')}"


#: 字体清单：画面实际注册了哪些字体，由它回答
FONT_MANIFEST_RELATIVE = Path("src/assets/fonts.json")


def font_files(repo_root: Path | None = None) -> list[Path]:
    """画面实际注册的字体文件。

    React 路径的字体是运行时用 CSS Font Loading API 注册的，页面里没有
    `@font-face` 可解析，因此缺字检查不能再去读样式表——它必须读**清单**，
    也就是注册代码自己读的那一份。清单与代码分开读同一份文件，
    正是为了让「注册了却没检查」这类漂移不可能发生。
    """
    manifest_path = web_dir(repo_root) / FONT_MANIFEST_RELATIVE
    if not manifest_path.is_file():
        raise A2VError(f"字体清单不存在: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise A2VError(f"字体清单不是合法 JSON: {manifest_path}: {exc}") from exc

    # 清单里的 sourceDirFromWeb 相对 **web/ 工程根**（与同步脚本的约定一致），
    # 不是相对清单自身的位置
    base = (web_dir(repo_root) / str(manifest.get("sourceDirFromWeb") or "")).resolve()
    missing: list[str] = []
    fonts: list[Path] = []
    for entry in manifest.get("files") or []:
        candidate = (base / str(entry.get("file") or "")).resolve()
        if candidate.is_file():
            fonts.append(candidate)
        else:
            missing.append(str(candidate))
    if missing:
        raise A2VError(
            "字体清单声明的字体文件不存在：" + "、".join(missing) + f"（清单：{manifest_path}）"
        )
    return fonts


@contextlib.contextmanager
def serve_contract_page(
    storyboard: str | Path,
    workspace_root: str | Path,
    repo_root: Path | None = None,
) -> Iterator[str]:
    """起一台只服务契约页与分镜的静态服务器，产出可打开的 URL。

    静态根取工作区根（分镜与作品资产在这里），`web/` 与 skill 资产走别名，
    因此内容根外置时同样成立。
    """
    page = require_contract_page(repo_root)
    mounts = mounts_for_contract_page(repo_root)
    with LocalServer(Path(workspace_root), mounts=mounts) as server:
        url = server.url_for(page)
        yield with_storyboard_query(url, storyboard_url(storyboard, workspace_root))
