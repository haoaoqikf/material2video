"""对作品内合成记录做配方和版本核验。"""
from m2v.core.errors import M2VError
from m2v.core.validate import integer, number, obj

VERSION = 1
# 与作品本地生成器 v1 的配方默认值一致。
DURATIONS_MS = {
    "keyboard-key": 160,
    "keyboard-typing": 3000,
    "mouse-click": 120,
    "switch": 180,
    "spark": 650,
    "electric-crackle": 1800,
    "electric-hum": 2000,
    "whoosh": 600,
    "impact-soft": 350,
    "impact-metal": 1200,
    "success": 700,
    "warning": 650,
}


def recipe(value: dict) -> dict:
    value = obj(value, "synthesis", {"name", "seed", "durationMs", "intensity", "rate", "eventsMs"})
    name = value.get("name")
    if not isinstance(name, str) or name not in DURATIONS_MS:
        raise M2VError("未知合成音效，请按声音指南检查 sound-recipe.json")
    result = {"name": name, "seed": integer(value.get("seed", 0), 0, 2**32-1, "seed"),
              "durationMs": integer(value.get("durationMs", DURATIONS_MS[name]), 30, 30000, "durationMs"),
              "intensity": number(value.get("intensity", .7), .05, 1, "intensity"),
              "rate": number(value.get("rate", 7), 1, 20, "rate")}
    if "eventsMs" in value:
        events = value["eventsMs"]
        if name != "keyboard-typing" or not isinstance(events, list) or not 1 <= len(events) <= 600:
            raise M2VError("eventsMs 仅支持 keyboard-typing，须有 1～600 个时间点")
        for event in events:
            integer(event, 0, result["durationMs"] - 1, "eventsMs")
        if events != sorted(set(events)):
            raise M2VError("eventsMs 必须严格递增且无重复")
        result["eventsMs"] = events
    return result
