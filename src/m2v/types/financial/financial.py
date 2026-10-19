"""金融类型的公开面：类型常量与两个职责模块的重导出。

实现按职责拆开：`materials.py` 负责材料契约与校验，`plan.py` 负责折线编排、节奏锚点与
显式迁移。本模块只声明类型常量并重导出公开名，使 `from m2v.types.financial import financial`
与 `financial.X` 的既有用法保持不变；私有校验辅助留在各自的实现模块里。
"""
from m2v.core.video_config import FPS
from .materials import (
    MATERIALS,
    WIDTH,
    HEIGHT,
    LAYOUT_BOUNDS_X,
    LAYOUT_BOUNDS_Y,
    CANVAS_CENTER_Y,
    load_project,
    render_inputs_digest,
    build_render_props,
)
from .plan import build_line_plan, frame_date, migrate_line, prepare_line_plan

__all__ = ['FPS', 'MATERIALS', 'WIDTH', 'HEIGHT', 'LAYOUT_BOUNDS_X', 'LAYOUT_BOUNDS_Y', 'CANVAS_CENTER_Y', 'load_project', 'render_inputs_digest', 'build_render_props', 'build_line_plan', 'prepare_line_plan', 'migrate_line', 'frame_date']
