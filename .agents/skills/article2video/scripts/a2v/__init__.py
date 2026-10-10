"""article2video 渲染工具包。

把 v4 分镜渲染为竖屏 MP4：分镜校验、媒体准备、共享 Remotion composition
逐帧渲染与 ffmpeg 音视频合成。模块按职责分组：

- storyboard_v4 / catalog:   当前分镜结构校验、受控原语目录
- paths / assets:            仓库根与工作区根、文章归属推导、本地资产定位
- browser / contract_page:   __A2V__ 契约检查与共享契约页
- remotion / source_policy:  composition 打包、源码确定性闸门与渲染执行
- render / production:       渲染编排、成片验收与交付
- fonts / media / beats:     字体覆盖与子集化、配音媒体清单、语义节拍
- inspect / keynote / motion: 体检量测、观感闸门与动效量测
- errors / cli:              可预期失败的统一基类与命令行入口
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
