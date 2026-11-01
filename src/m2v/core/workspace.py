"""工作区根解析：仓库根、内容根与两者的关系。

作品是**内容**，仓库是**工具链**，两者可以分开放，因此这里区分两层根：

```text
仓库根 repo_root        # .agents/skills/material2video/SKILL.md 所在处：脚本、共享资产、examples
工作区根 workspace_root # 存放 videos/<类型路径>/<slug> 与作品产物的目录
```

工作区根按 `--content-root` > `M2V_CONTENT_ROOT` > 仓库根 解析：不设内容根时
两层根重合，既有调用方式不变；设了内容根，作品与产物就可以留在仓库之外。

本模块只负责「根在哪」，不推导作品目录结构；作品目录结构由各类型自己的
路径逻辑决定。
"""

from __future__ import annotations

import os
from pathlib import Path

from m2v.core.assets import BUNDLE_DIR

# 仓库根标记：skill 主文档的位置。它同时是「这个目录属于 material2video 仓库」的证据。
PROJECT_MARKER = Path(".agents/skills/material2video/SKILL.md")

#: 内容根环境变量：让作品与产物留在仓库之外的目录里。
#: 命令行参数 `--content-root` 优先于它，两者都没有时工作区根就是仓库根。
CONTENT_ROOT_ENV = "M2V_CONTENT_ROOT"


def bundle_repo_root() -> Path | None:
    """正在运行的 skill bundle 所在的仓库根。

    作品落在仓库之外时，从输入文件向上是找不到标记的；而「哪份共享资产会被
    挂载、哪份共享页面会被使用」由正在运行的脚本决定，因此这时仓库根取脚本
    自身的位置。bundle 不在仓库里（被拷出去单独使用）时返回 None。
    """
    candidate = BUNDLE_DIR.parents[2]
    return candidate if (candidate / PROJECT_MARKER).is_file() else None


def content_root(explicit: str | Path | None = None) -> Path | None:
    """解析内容根：`--content-root` 优先于环境变量 `M2V_CONTENT_ROOT`。

    两者都没有时返回 None，表示「工作区根就是仓库根」——这与引入内容根之前
    的行为完全一致，既有调用方式不需要改。相对路径按当前工作目录解析，
    与其他命令行参数的口径一致。
    """
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    from_env = os.environ.get(CONTENT_ROOT_ENV, "").strip()
    if from_env:
        return Path(from_env).expanduser().resolve()
    return None
