"""金融数据来源的公开面：材料、投资计算与折线计划。

实现按职责拆开：`materials.py` 负责材料契约与校验，`plan.py` 负责折线编排、节奏锚点与
计划生成。本模块只声明类型常量并重导出公开名，使 `from m2v.types.financial import financial`
供新版结构化来源使用；私有校验辅助留在各自的实现模块里。
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
    build_render_props,
)
from .plan import build_line_plan, frame_date, prepare_line_plan

__all__ = ['FPS', 'MATERIALS', 'WIDTH', 'HEIGHT', 'LAYOUT_BOUNDS_X', 'LAYOUT_BOUNDS_Y', 'CANVAS_CENTER_Y', 'load_project', 'build_render_props', 'build_line_plan', 'prepare_line_plan',  'frame_date']
