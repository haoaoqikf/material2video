"""Shared fixed video frame rate."""
import json
from m2v.core.assets import REPOSITORY_ROOT

FPS: int = json.loads((REPOSITORY_ROOT / "web/src/video-config.json").read_text(encoding="utf-8"))["fps"]
