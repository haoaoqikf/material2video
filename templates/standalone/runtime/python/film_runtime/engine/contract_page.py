"""本作品的渲染契约页定位及本地URL组装；构建产物在dist/contract，资源全部属于作品。"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

import film_runtime.core.assets as assets
from film_runtime.core.errors import VideoError
from film_runtime.engine.http_server import LocalServer

#: `web/` 目录的服务器别名前缀。页面在这里，分镜在工作区根里，靠它接起来。
WEB_MOUNT = "/__m2v_web__"

#: 契约页相对作品根 的位置：Vite 的构建产物
CONTRACT_PAGE_RELATIVE = Path("dist/contract/contract.html")

#: 构建命令：报错信息里要给出可照抄的一条命令
BUILD_HINT = "pnpm install --frozen-lockfile && pnpm run build"


def repository_root() -> Path:
    """仓库根：由本地运行模块位置推出，与作品放在哪里无关。

    由本地运行模块固定位置推导作品根，不读取主项目或Skill。
    """
    return assets.REPOSITORY_ROOT


def web_dir(repo_root: Path | None = None) -> Path:
    """前端工程目录。"""
    return repo_root or repository_root()


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
        raise VideoError(
            f"渲染契约页不存在: {page}\n"
            f"它是画面与渲染入口之间的接口，需要先用 Vite 构建：{BUILD_HINT}"
        )
    return page


def web_mounts(repo_root: Path | None = None) -> dict[str, Path]:
    """契约页所在的挂载表：别名前缀 → `web/` 目录。"""
    directory = web_dir(repo_root)
    if not directory.is_dir():
        raise VideoError(
            f"前端工程目录不存在: {directory}\n"
            f"画面实现与契约页都在它下面，请确认仓库结构完整：{BUILD_HINT}"
        )
    return {WEB_MOUNT: directory}


def mounts_for_contract_page(repo_root: Path | None = None) -> dict[str, Path]:
    """契约页路径上的完整挂载表。

    同时挂载契约页与 skill 资产，体检与渲染共用一台静态服务器。
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
        raise VideoError(
            f"分镜不在工作区根内，契约页取不到它：分镜 {resolved}，工作区根 {root}"
        ) from exc


def with_storyboard_query(url: str, storyboard_path: str) -> str:
    """给契约页 URL 补上 `m2v-storyboard` 查询参数。"""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}m2v-storyboard={quote(storyboard_path, safe='')}"


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
        raise VideoError(f"字体清单不存在: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise VideoError(f"字体清单不是合法 JSON: {manifest_path}: {exc}") from exc

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
        raise VideoError(
            "字体清单声明的字体文件不存在：" + "、".join(missing)
            + f"（清单：{manifest_path}；请运行 uv run python fonts/fetch.py 恢复）"
        )
    return fonts


@contextlib.contextmanager
def serve_page(
    page: Path,
    storyboard: str | Path,
    workspace_root: str | Path,
    repo_root: Path | None = None,
) -> Iterator[str]:
    """起一台只服务指定契约页与材料的静态服务器。"""
    mounts = mounts_for_contract_page(repo_root)
    with LocalServer(Path(workspace_root), mounts=mounts) as server:
        url = server.url_for(page)
        yield with_storyboard_query(url, storyboard_url(storyboard, workspace_root))


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
    with serve_page(page, storyboard, workspace_root, repo_root) as url:
        yield url
