"""完整预演自动门禁，与可选人工画面评审独立。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.engine import output_validation


def require_preview(root: Path, prepared: dict, *, verify_media: bool = True) -> dict:
    """验证当前完整预演；状态查询只检查绑定，导出前另做全片解码。"""
    try:
        record = json.loads((root / "outputs/preview-record.json").read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("预演记录不是对象")
        frames = record.get("frames")
        if (record.get("preparedFingerprint") != prepared["preparedFingerprint"]
                or type(frames) is not int or frames != prepared["durationInFrames"]):
            raise ValueError("预演指纹或完整帧数不匹配")
        # 自带示例的预演位于 videos/examples，允许记录中的相对路径含 ..。
        path = record.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("预演路径无效")
        video = (root / path).resolve()
        if (not video.is_file()
                or hashlib.sha256(video.read_bytes()).hexdigest() != record.get("sha256")):
            raise ValueError("预演文件缺失或摘要不匹配")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise M2VError("缺少有效的当前完整预演；请重新执行 m2v preview") from exc
    if verify_media:
        output_validation.verify_output(video, frames, prepared["width"], prepared["height"],
                                        prepared["fps"],
                                        expect_audio=bool(prepared.get("audio", {}).get("segments")))
    return record
