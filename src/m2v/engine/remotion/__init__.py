"""Node 侧的逐帧渲染与编码：Python 与 Remotion 之间唯一的边界。

职责划分是刻意的：Python 保留分镜校验、路径归属推导、配音与字幕准备、体检编排、
溯源与交付文件权限修复；Node 只负责**画面执行**——把 React composition 逐帧
渲染并编码成无声 MP4。因此这里只有「起进程、解析它报出来的行、把失败翻译成
能定位的错误」三件事，没有任何判定逻辑。

两边靠 stdout 上**带前缀的行**通信：

- `__M2V_SESSION__{...}`：会话信息（浏览器开了几个、选中了哪个 composition）；
- `__M2V_COMPOSITION__{...}`：composition 的真实元数据，渲染前就报出来，
  供渲染入口与分镜交叉校验；
- `__M2V_READY__`：元数据已报出，正在等 Python 的确认；
- `__M2V_DONE__{...}`：渲染完成；
- `__M2V_PROGRESS__<百分比>`：渲染进度。

反向只有两种行：`__M2V_CONFIRM__{...}` 表示校验通过、可以开始渲染，
`__M2V_ABORT__{...}` 表示校验没过、立即退出。**先握手再渲染**是刻意的：
composition 的时长由 props 推导，与分镜累计时长是两份可能不一致的数据，
让不一致的画面先渲完再发现，代价是整段渲染时间。

为什么不用退出码或日志文本猜原因：`remotion` 的日志面向人看，措辞会随版本变化；
把判定挂在日志上，升级一次就会静默失效。

实现按职责拆在同一个包的四个模块里：:mod:`~m2v.engine.remotion.process`（进程与
环境）、:mod:`~m2v.engine.remotion.bundling`（打包与缓存）、
:mod:`~m2v.engine.remotion.session`（渲染会话与两条旧路径）、
:mod:`~m2v.engine.remotion.inputs`（输入指纹与入口常量）。本模块只做重导出，
`import m2v.engine.remotion as remotion` 与 `remotion.X` 的用法与拆包前完全一致。

替换私有实现（测试里的 `_spawn`、`_run`、`_bundle_into` 之类）必须打在**真正执行
它的那个子模块**上：包上的同名绑定只是重导出的副本，改它不会影响子模块内部的调用。
"""

from __future__ import annotations

# 下面这些标准库名字是拆包前模块命名空间的一部分：`remotion.X` 的全部既有用法
# （包括 `remotion.os` 这类少见但合法的取用）都要保持可用，因此原样重导出。
import contextlib
import json
import logging
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import m2v.core.assets as assets
import m2v.core.source_policy as source_policy
import m2v.engine.bundle_cache as bundle_cache
import m2v.engine.contract_page as contract_page
import m2v.engine.perf as perf
from m2v.core.errors import M2VError
from m2v.core.fingerprints import file_digest, fingerprint as calculate_fingerprint

from .bundling import BundleOutcome, _bundle_into, bundle
from .inputs import (
    ENTRY_POINT,
    WORK_MOUNT_PREFIX,
    _ENTRY_ROOTS,
    _PACKAGE_FILES,
    _imports_of,
    build_input_fingerprint,
    build_inputs,
    fingerprint_mounts,
    web_dir,
)
from .process import (
    ABORT_PREFIX,
    CONFIRM_PREFIX,
    DEFAULT_CONCURRENCY,
    DONE_PREFIX,
    METADATA_PREFIX,
    PROGRESS_PREFIX,
    READY_PREFIX,
    RENDER_SCRIPT,
    SESSION_PREFIX,
    RemotionError,
    _ABORT_GRACE_S,
    _BUNDLE_TIMEOUT_S,
    _EOF,
    _EXIT_GRACE_S,
    _LineReader,
    _METADATA_TIMEOUT_S,
    _run,
    _spawn,
    _tail_text,
    _terminate_tree,
    check_concurrency,
    program,
)
from .session import (
    CompositionMetadata,
    _metadata_from,
    _safe_int,
    metadata,
    progress_handler,
    render_frames,
    render_session,
    render_still,
)

logger = logging.getLogger(__name__)

#: 拆包前的模块没有 `__all__`，通配导入取的就是「全部非下划线名字」；这里保持同一份
#: 名单（含标准库名字），另加包级的 :func:`implementation_files`。
__all__ = [
    'ABORT_PREFIX', 'BundleOutcome', 'CONFIRM_PREFIX', 'Callable', 'CompositionMetadata',
    'DEFAULT_CONCURRENCY', 'DONE_PREFIX', 'ENTRY_POINT', 'M2VError', 'METADATA_PREFIX',
    'PROGRESS_PREFIX', 'Path', 'READY_PREFIX', 'RENDER_SCRIPT', 'RemotionError',
    'SESSION_PREFIX', 'WORK_MOUNT_PREFIX', 'annotations', 'assets', 'build_input_fingerprint',
    'build_inputs', 'bundle', 'bundle_cache', 'calculate_fingerprint', 'check_concurrency',
    'contextlib', 'contract_page', 'dataclass', 'file_digest', 'fingerprint_mounts', 'json',
    'logger', 'logging', 'metadata', 'os', 'perf', 'program', 'progress_handler', 'queue', 're',
    'render_frames', 'render_session', 'render_still', 'shutil',
    'signal', 'source_policy', 'subprocess', 'threading', 'time', 'uuid', 'web_dir',
    'implementation_files',
]


def implementation_files() -> list[Path]:
    """本包的全部实现文件（按路径排序）。

    拆包后 `Path(remotion.__file__)` 只指向做重导出的 `__init__.py`，实现改动
    不再进摘要。需要把渲染实现纳入指纹的调用方（成片溯源、候选过期判定）必须
    改用这里逐个文件覆盖，否则「改了实现却判成当前」。

    口径复用 :func:`m2v.core.fingerprints.module_files`：包里还有子包时同样
    逐个 `.py` 算进去，与通用类型、代码场景的摘要保持同一套定义。
    """
    import sys
    from m2v.core.fingerprints import module_files

    return module_files(sys.modules[__name__])


def __dir__() -> list[str]:
    """公开面与拆包前一致：子模块本身是实现细节，不进 `dir()`。"""
    return sorted(set(globals()) - {"inputs", "process", "session"})
