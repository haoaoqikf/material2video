"""按作品声音声明判定交付是否需要音轨，不把内部静音母版当成用户声音。"""
from __future__ import annotations


def declared_audio(prepared: dict) -> bool:
    """旁白、音乐或音效任一存在时交付有声；全部为空时交付零音频流。"""
    props = prepared.get("props") or {}
    soundtrack = props.get("soundtrack") or {}
    return bool(soundtrack.get("music") or soundtrack.get("effects") or
                any(scene.get("narrationSegments") for scene in props.get("compiledScenes", [])))
