"""Restore the exact locally provided voice used by this example."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("音色登记必须是 JSON 对象")
    return data


def ensure_available(path: Path, data: bytes) -> None:
    if path.is_symlink() or (path.exists() and path.read_bytes() != data):
        raise ValueError(f"目标已有不同内容，请先备份并移开：{path.name}")


def install(path: Path, data: bytes) -> None:
    if path.exists():
        ensure_available(path, data)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        temporary.write_bytes(data)
        # Publish the full file without overwriting an installation made concurrently.
        try:
            os.link(temporary, path)
        except FileExistsError:
            ensure_available(path, data)
    finally:
        temporary.unlink()


def restore(here: Path, source_registry: Path, source_audio: Path) -> None:
    expected = read_json(here / "voice-requirements.json")
    registry = read_json(source_registry)
    if not isinstance(registry.get("voices"), list):
        raise ValueError("源登记缺少音色列表")
    profiles = [entry for entry in registry["voices"]
                if isinstance(entry, dict) and entry.get("voice") == expected["voice"]]
    if len(profiles) != 1:
        raise ValueError("源登记必须包含且只包含一份目标音色档案")
    profile = profiles[0]
    # 忽略 JSON 排版和字段顺序，校验整份原档案，包括参考文本和授权记录。
    profile_bytes = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(profile_bytes).hexdigest() != expected["profileSha256"]:
        raise ValueError("音色档案摘要不符")

    audio = source_audio.read_bytes()
    if len(audio) != expected["bytes"] or hashlib.sha256(audio).hexdigest() != expected["sha256"]:
        raise ValueError("参考 WAV 的大小或摘要不符")

    restored = read_json(here / "registry.template.json")
    restored["voices"] = [profile]
    registered = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    local_registry = here / "registry.json"
    files = (here.parent / "files").resolve()
    local_audio = files / expected["refAudio"]
    if not local_audio.resolve().is_relative_to(files):
        raise ValueError("参考 WAV 目标路径越界")
    ensure_available(local_registry, registered)
    ensure_available(local_audio, audio)
    install(local_audio, audio)
    install(local_registry, registered)


def main() -> None:
    parser = argparse.ArgumentParser(description="从本地恢复复利示例的原克隆音色")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-project", type=Path, help="原作品目录")
    source.add_argument("--registry", type=Path, help="提供音色档案的 Qwen3-TTS 登记文件")
    parser.add_argument("--audio", type=Path, help="与 --registry 配合使用的原始参考 WAV")
    args = parser.parse_args()
    if args.source_project:
        if args.audio:
            parser.error("--source-project 已指定参考文件位置")
        reference = read_json(HERE / "voice-requirements.json")["refAudio"]
        registry = args.source_project / "models/qwen3-tts/registry.json"
        audio = args.source_project / "models/files" / reference
    else:
        if not args.audio:
            parser.error("--registry 需要同时指定 --audio")
        registry, audio = args.registry, args.audio
    try:
        restore(HERE, registry, audio)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"音色恢复失败：{exc}\n")
    print("原克隆音色校验并恢复成功")


if __name__ == "__main__":
    main()
