"""可信 React 场景构建与按需逐帧录制。准备绑定源码，最终合成回放录制片段。

v9 的作品代码控制整张画布：录制 viewport、页面根元素、ffmpeg 标准化与 composition
都用作品声明的画幅。共享层只提供片段回放与字幕，不再画标题或内容框。

模块按职责拆成两个：`config.py` 负责入口校验、录制配置与静态模块构建，`capture.py`
负责逐帧采集、片段缓存与编码验收。这里只做重导出，调用方继续写 `code_scenes.X`。
"""
from .capture import (PURE_CONTRACT, SEQUENTIAL_CONTRACT, materialize, record, _valid_clip, _clip_receipt,
                      _cached_ranges, _is_hero_frame, _subframes_for, _average, _capture, _encode, _verify_clip)
from .config import digest, validate_entry, validate_capture, capture_settings, implementation_inputs, scene_config, build_scene, source_texts, media_files

__all__ = ['PURE_CONTRACT', 'SEQUENTIAL_CONTRACT', 'build_scene', 'capture_settings', 'digest', 'implementation_inputs', 'materialize', 'media_files', 'record', 'scene_config', 'source_texts', 'validate_capture', 'validate_entry']
