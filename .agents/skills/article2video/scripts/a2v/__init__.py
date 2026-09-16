"""article2video 渲染工具包。

把「动画网页」渲染为竖屏 MP4 的最小实现：分镜校验、Playwright 逐帧截图、
ffmpeg 管道编码。模块划分：

- storyboard: 分镜脚本模型与结构校验
- paths:      项目根识别、文章归属推导与标准输出路径
- browser:    Playwright 会话与 __A2V__ 契约检查
- encoder:    ffmpeg 子进程管道
- render:     帧循环编排与成片验收
- errors:     可预期失败的统一基类
- cli:        命令行入口
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
