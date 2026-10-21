"""Shared fixed video frame rate and default reading hold."""
import json
from m2v.core.assets import REPOSITORY_ROOT

FPS: int = json.loads((REPOSITORY_ROOT / "web/src/video-config.json").read_text(encoding="utf-8"))["fps"]
#: 未声明阅读停留时，通用 v8 在每个末段后保留的默认时长（秒）。
READING_TAIL_SECONDS: float = 0.4
