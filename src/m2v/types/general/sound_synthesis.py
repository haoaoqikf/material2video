"""常见动作的确定性拟音；配方显式保存，渲染阶段不随机选音。"""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import struct
import wave

from m2v.core.errors import M2VError
from m2v.core.validate import integer, number, obj
from m2v.engine.audio import SAMPLE_RATE

VERSION = 1
# 时长是目录默认值；合成均为风格化拟音，不标作实录。
CATALOG = {
    "keyboard-key": ("操作", "单次键帽按下与回弹", 160, False),
    "keyboard-typing": ("操作", "连续打字；eventsMs 可对齐逐键动作", 3000, False),
    "mouse-click": ("操作", "鼠标按下与释放", 120, False),
    "switch": ("操作", "开关拨动", 180, False),
    "spark": ("电气", "短促火花噼啪", 650, False),
    "electric-crackle": ("电气", "连续不规则电气爆裂", 1800, False),
    "electric-hum": ("电气", "低频电流及谐波，可循环", 2000, True),
    "whoosh": ("运动", "滤波噪声掠过", 600, False),
    "impact-soft": ("碰撞", "低沉短促敲击", 350, False),
    "impact-metal": ("碰撞", "金属非谐波共振", 1200, False),
    "success": ("提示", "上行和声音符", 700, False),
    "warning": ("提示", "双脉冲警告", 650, False),
}


def catalog() -> list[dict]:
    return [{"name": name, "category": row[0], "description": row[1],
             "durationMs": row[2], "loopable": row[3], "source": "synthesized",
             "variants": ("durationMs/intensity 控制时长与力度" if name in {"electric-hum", "success", "warning"}
                          else "seed 控制瞬态、音色或节奏；intensity 控制力度")}
            for name, row in CATALOG.items()]


def recipe(value: dict) -> dict:
    value = obj(value, "synthesis", {"name", "seed", "durationMs", "intensity", "rate", "eventsMs"})
    name = value.get("name")
    if not isinstance(name, str) or name not in CATALOG:
        raise M2VError("未知合成音效，请用 sounds catalog 查询")
    result = {"name": name, "seed": integer(value.get("seed", 0), 0, 2**32-1, "seed"),
              "durationMs": integer(value.get("durationMs", CATALOG[name][2]), 30, 30000, "durationMs"),
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


def synthesize(value: dict, target: Path) -> dict:
    settings = recipe(value)
    name, duration = settings["name"], settings["durationMs"] / 1000
    rng = random.Random(settings["seed"])
    samples = array("f", [0.]) * round(duration * SAMPLE_RATE)

    def transient(start: float, length: float, frequency: float, decay: float,
                  noise: float, gain: float = 1., metal: bool = False) -> None:
        begin = round(start * SAMPLE_RATE)
        phases = [rng.random() * math.tau for _ in range(3)] if noise else [0., 0., 0.]
        for i in range(min(round(length * SAMPLE_RATE), len(samples) - begin)):
            t = i / SAMPLE_RATE
            envelope = min(1., t / .0015) * math.exp(-decay * t) * min(1., (length-t)/.008)
            tone = math.sin(math.tau * frequency * t + phases[0])
            if metal:
                tone = sum(math.sin(math.tau * frequency * ratio * t + phase)
                           for ratio, phase in zip((1., 2.756, 5.404), phases)) / 3
            noise_sample = noise * rng.uniform(-1, 1) if noise else 0.
            samples[begin+i] += gain * envelope * ((1-noise) * tone + noise_sample)

    if name in {"keyboard-key", "keyboard-typing", "mouse-click", "switch"}:
        times = [0.]
        if name == "keyboard-typing":
            times = [t/1000 for t in settings["eventsMs"]] if "eventsMs" in settings else []
            if "eventsMs" not in settings:
                t = 0.
                while t < duration:
                    times.append(t)
                    t += rng.uniform(.6, 1.5) / settings["rate"]
        for t in times:
            frequency = (rng.uniform(900, 1800) if name == "mouse-click" else
                         rng.uniform(120, 260) if name == "switch" else rng.uniform(350, 750))
            transient(t, .055, frequency, 70, .3 if name == "switch" else .65, rng.uniform(.6, 1.))
            transient(t+(.065 if name == "switch" else .035), .06, frequency*1.7, 80, .4, .35)
    elif name in {"spark", "electric-crackle"}:
        t = 0.
        while t < duration:
            transient(t, rng.uniform(.012, .06), rng.uniform(1800, 5000), 95, .85, rng.uniform(.25, 1.))
            t += rng.uniform(.015, .12) if name == "spark" else rng.uniform(.025, .2)
    elif name == "electric-hum":
        # 所有频率均落在循环长度的整数周期，接缝无随机噪声跳变。
        cycles = max(1, round(60 * duration))
        for i in range(len(samples)):
            phase = math.tau * i / len(samples)
            samples[i] = .6 * math.sin(cycles*phase) + .2 * math.sin(2*cycles*phase) + .1 * math.sin(7*cycles*phase)
    elif name == "whoosh":
        low = 0.
        for i in range(len(samples)):
            p = i / len(samples)
            noise = rng.uniform(-1, 1)
            low += (.02 + .65 * math.sin(math.pi*p)**2) * (noise-low)
            samples[i] = low * math.sin(math.pi*p)**2
    elif name.startswith("impact-"):
        transient(0, duration, rng.uniform(160, 230) if name == "impact-metal" else 85,
                  5 if name == "impact-metal" else 20, .12 if name == "impact-metal" else .3,
                  metal=name == "impact-metal")
    else:
        notes = (660, 830.61, 987.77) if name == "success" else (440, 440)
        for index, frequency in enumerate(notes):
            transient(index * duration / len(notes), duration / len(notes), frequency, 8, 0, .8)
    if name != "electric-hum":
        # 显式按键可以靠近片尾；统一收尾避免最后一次瞬态被硬切产生爆音。
        tail = min(len(samples), round(.005*SAMPLE_RATE))
        for i in range(tail):
            samples[-tail+i] *= (tail-1-i)/tail
    peak = max((abs(s) for s in samples), default=1.) or 1.
    scale = min(1., .85/peak) * settings["intensity"] * 32767
    with wave.open(str(target), "wb") as out:
        out.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        # 分块编码，避免多份大 PCM 字节数组同时驻留。
        for offset in range(0, len(samples), SAMPLE_RATE):
            out.writeframesraw(b"".join(struct.pack("<h", round(s*scale)) for s in samples[offset:offset+SAMPLE_RATE]))
    return {"generator": "m2v.sound-synthesis", "version": VERSION, "parameters": settings}
