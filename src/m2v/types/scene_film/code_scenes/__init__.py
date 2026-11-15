"""五类统一 v9 代码场景的材料校验入口。

采集、构建与渲染由作品本地运行时执行；主项目只校验分镜声明。
"""
from .config import validate_capture, validate_entry

__all__ = ['validate_capture', 'validate_entry']
