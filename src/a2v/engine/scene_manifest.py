"""当前作品代码场景的静态清单：解析、生成与覆盖。

preview / review / render 每次运行前都要重建 ``web/.gen/active-scenes.ts``：
清单只包含**当前作品**分镜引用的代码场景模块，整体覆盖生成——上一支作品
的模块引用不会残留，失败或中断后下次运行也会重写而不是复用未知状态。

分工沿用 Python / Node 边界：Python 解析作品归属、把允许的场景入口
（模块标识 → 绝对路径）写进 ``scene-manifest.json``；Node 生成脚本负责
路径转义并写出静态 import。静态 import 让 TypeScript、Vite 与 Remotion
webpack 都能解析仓库外内容根的模块，也让模块进入可达导入图与源码指纹。
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import a2v.core.code_scenes as code_scenes
import a2v.engine.remotion as remotion
from a2v.core.errors import A2VError

#: 生成产物相对 `web/` 的位置。目录整体在 .gitignore 中。
GENERATED_MANIFEST = Path(".gen/active-scenes.ts")

#: 传给 Node 生成器的清单文件（同样在 .gen/ 下，随产物一起被覆盖）。
MANIFEST_INPUT = Path(".gen/scene-manifest.json")

#: 生成脚本相对 `web/` 的位置。
GENERATOR_SCRIPT = "scripts/gen-active-scenes.mjs"

#: 清单生成的超时：一次文件写入按秒计，超时意味着环境出了别的问题。
_GENERATE_TIMEOUT_S = 120


@dataclass(frozen=True)
class SceneModule:
    """一个被分镜引用并解析成功的代码场景模块。"""

    id: str
    path: Path


def collect(data: dict, article_source_dir: str | Path) -> list[SceneModule]:
    """解析分镜中的全部代码场景模块；缺失或越界直接报错。

    去重按模块标识：两幕共用同一模块时只生成一份 import。
    """
    modules: dict[str, SceneModule] = {}
    for scene_path, _scene, module in code_scenes.iter_code_scenes(data):
        if not module or module in modules:
            continue
        resolved = code_scenes.resolve_module(article_source_dir, module)
        if resolved is None:
            raise A2VError(
                f"代码场景模块不存在：{module}（{scene_path}）；"
                f"作品目录：{Path(article_source_dir)}"
            )
        modules[module] = SceneModule(id=module, path=resolved)
    return list(modules.values())


def generate(
    *,
    web_dir: str | Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
) -> Path:
    """为当前作品重建静态场景清单，返回生成文件路径。

    分镜没有代码场景时也走同一条路径：生成空映射并覆盖旧文件，
    保证「切换到纯 tree 作品」同样不残留上一个作品的模块。
    """
    web = Path(web_dir)
    try:
        data = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise A2VError(f"分镜读取失败，无法生成代码场景清单：{exc}") from exc

    modules: list[SceneModule] = []
    article_dir: str | None = None
    workspace_root: str | None = None
    if any(True for _ in code_scenes.iter_code_scenes(data)):
        source_dir = Path(storyboard_path).resolve().parent
        modules = collect(data, source_dir)
        article_dir = str(source_dir)
        if content_root:
            workspace_root = str(Path(content_root).resolve())
        else:
            workspace_root = str(source_dir.parent.parent.resolve())

    manifest = {
        "webDir": str(web.resolve()),
        "outFile": GENERATED_MANIFEST.as_posix(),
        # Tailwind source 索引用：指向当前作品目录（scenes/ 与 assets/）
        "articleDir": article_dir,
        # 指纹挂载用：作品文件以 __a2v_workspace__ 前缀记录可复核键
        "workspaceRoot": workspace_root,
        "modules": [{"id": item.id, "module": str(item.path.resolve())} for item in modules],
    }
    manifest_path = (web / MANIFEST_INPUT).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    remotion.require_environment(web)
    remotion._run(
        [remotion.program("node"), GENERATOR_SCRIPT, "--manifest", str(manifest_path)],
        cwd=web,
        timeout_s=_GENERATE_TIMEOUT_S,
        what="生成代码场景静态清单",
    )
    target = web / GENERATED_MANIFEST
    if not target.is_file():
        raise A2VError(f"代码场景清单生成后没有产物：{target}")
    return target


def generate_to_temp(
    *, web_dir: str | Path, modules: list[tuple[str, str]]
) -> tuple[Path, Path]:
    """把清单生成到临时目录（测试夹具用），返回 (生成文件, 临时目录)。

    ``modules`` 是 (模块标识, 模块绝对路径) 列表；不走分镜解析，
    供跨根夹具直接验证 import 描述符的形态与可解析性。
    """
    web = Path(web_dir)
    temp = Path(tempfile.mkdtemp(prefix="a2v-manifest-"))
    manifest = {
        "webDir": str(web.resolve()),
        # 生成器按 webDir 解析 outFile；绝对路径同样成立（测试夹具用）
        "outFile": str((temp / "active-scenes.ts").resolve()).replace("\\", "/"),
        "modules": [{"id": module_id, "module": module_path} for module_id, module_path in modules],
    }
    manifest_path = temp / "scene-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    remotion.require_environment(web)
    remotion._run(
        [remotion.program("node"), GENERATOR_SCRIPT, "--manifest", str(manifest_path)],
        cwd=web,
        timeout_s=_GENERATE_TIMEOUT_S,
        what="生成代码场景静态清单（临时）",
    )
    return temp / "active-scenes.ts", temp
