"""观感闸门：把「发布会级别的画面」里能被量出来的部分跑一遍。

和 `constitution.py` 的分工：

| 模块 | 回答的问题 | 判据性质 |
| --- | --- | --- |
| `constitution.py` | 这是不是一段**废片** | 结构、曲线、挂载点、文案真源 |
| 本模块 | 这像不像**发布会级别的画面** | 留白、强调色、层级、对比度、对齐 |

两者**分开报告、分开计数**。混在一个总分里，会让「画面很空但结构齐全」看起来及格。

每条闸门给出实测数值与阈值，**不能实测时报告 skipped 并写明原因**，
绝不计为通过——假自动判定比没有判定更危险。阈值与理由见
`references/keynote-design-system.md`。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

#: 与角落像素相差多少灰度级以内算「背景」。
#: 深色主题的背景带光晕与点阵，缩略图上的浮动比纯色底大，因此给到 16。
#: 文字与图形与背景的差距远大于这个值。
_BACKGROUND_TOLERANCE = 16

#: 强调色判定容差（每通道）。只用于统计「纯色」子集的诊断值，不再作判据。
_ACCENT_TOLERANCE = 46

#: 强调色**族**的判据：色度下限（max−min）与色相容差（度）。
#:
#: 原先的判据是「与纯强调色逐通道相差 ≤ 46」的色盒，它看不见设计系统自己
#: 登记的另外三个强调色成员——实测距离：
#:   `--a2v-accent-line`（alpha 0.55）合成 RGB(32,122,146)  通道差 87/102
#:   `--a2v-accent-deep`（#2f7fa8，文档写的是「图形着重色」） 通道差 87/87
#:   `--a2v-accent-soft-solid`（#16465f，焦点面的填充）     通道差 160
#: 于是「用强调色着重色画的焦点」被 K2 判成「没有强调色」。逐通道色盒本来
#: 也不是感知量：它同时排斥变暗与变亮的同色。
#:
#: 换成感知量：**色度**（离中性轴的距离）+ **色相**。各族成员实测色度：
#:   背景梯度 4 / `--fig-surface` 20 / `--a2v-accent-soft`(0.14) 合成 32
#:   `--a2v-accent-soft-solid` 73 / `--a2v-accent-line` 合成 114
#:   `--a2v-accent-deep` 121 / 纯强调色 205
#: 取 50 干净地切开：背景与中性面（色度 4–20）被排除，
#: 四个强调色成员（73–205）全部纳入。
#:
#: 为什么把 `--a2v-accent-soft`（0.14）也排除在外：14% 透明度的染色只是**暗示**，
#: 在近黑底上合成出 RGB(15,39,47)，读者不会把它读成"这里有一个焦点"。
#: 焦点要有可辨识的色块，色度下限就是这条线。
_ACCENT_CHROMA_MIN = 50

#: 色相容差。强调色 #32d6ff 是 192°，四个成员落在 192–200°；
#: 放宽到 ±30° 会覆盖 219° 的 `--fig-surface`，但它色度只有 20，已被色度下限挡掉。
_ACCENT_HUE_TOLERANCE = 30.0

#: 留白预算：按帧量测的「背景像素占比」。
#: 信息幕 ≥40%、hero/quote 幕 ≥60% 是设计研究里的可编码结论（见参考文档）。
#: 警告带宽 0.18：低于门槛一截才判失败，避免把「留白略紧」误报成「画面糊满了」。
_EMPTY_MIN_QUOTE = 0.60
_EMPTY_MIN_DEFAULT = 0.40
_EMPTY_WARN_MARGIN = 0.18

#: 一帧里「亮到能读的墨迹」的下限。低于它就只剩背景与暗色图形了，
#: 说明文字要么没画出来，要么被压暗到读不出。540×960 下 0.004 约等于 2000 像素，
#: 一排 40px 的正文就超过这个量。
_READABLE_MIN = 0.004

#: 强调色面积占比：60-30-10 结构里强调色占 10%。
#: 下限取 0.2%：一个强调短语、一条焦点线或一个主角数字在整帧里就是千分之几的量级，
#: 门槛定高了会把「只有一个焦点」误判成「没有焦点」。
_ACCENT_MIN = 0.002
_ACCENT_MAX = 0.15
_ACCENT_FAIL = 0.25

#: 单帧字号种类上限：层级靠字号阶，不靠「稍微大一点」。
#: 只统计不小于该字号的元素：图形标注、轴名、角标这类小字是辅助信息，
#: 与「主体层级」不是一回事；把它们算进来会把所有含图形的画面判成失败。
_MAX_TYPE_SIZES = 4
_TYPE_COUNT_FLOOR = 44

#: 对齐基线：正文块左边界之间的最大允许离散（px）。
_ALIGN_TOLERANCE = 12

#: 一帧里允许出现的对齐线数量：一条居中 + 一条左对齐是常见的合法组合。
_MAX_ALIGN_LINES = 2

#: 居中判据：文本块中心与安全区中心相差不超过该值即视为居中
_ALIGN_CENTER_TOLERANCE = 6

#: 对齐判定至少要几个文本块才有意义
_ALIGN_MIN_SAMPLES = 2

#: 对齐判定用的最小字号：比它小的元素（图形标注、角标）不参与
_ALIGN_MIN_FONT = 44

#: 镜像判据：两条左对齐线上的文本块，中心之和与画面中心的两倍相差不超过该值，
#: 就认为它们是一对**关于画面中心镜像**的对称栏。
#:
#: 为什么需要这一条：左右两栏的正文块各自向自己所在栏的左边对齐（这是正确的做法），
#: 它们的左边界必然不同，但中心关于画面中心镜像。
#: 实测 compare 一幕的两张卡片标签：左 267 / 左 637，中心 355 / 725，
#: 355 + 725 = 1080 = 2 × 540（画面中心）——是标准的两栏对称构图，
#: 而按左边界聚类会数成两条线，于是「居中标题 + 对称两栏」被判成「散」。
#: 取 12px 与左边界聚类同量级：足以容纳两栏文字宽度的细微差异，
#: 又不至于把互不相干的文本块并到一起（散乱排布的左边界不会恰好成镜像对）。
_ALIGN_MIRROR_TOLERANCE = 12

#: 对比度下限：正文 7:1（AAA），大字与图形 4.5:1
_CONTRAST_BODY = 7.0
_CONTRAST_LARGE = 4.5
_LARGE_TEXT_PX = 44


@dataclass
class Gate:
    """一条观感闸门的实测结论。"""

    id: str
    title: str
    status: str  # pass / warn / fail / skipped
    value: Any = None
    threshold: Any = None
    detail: str = ""
    scene: str = ""

    def format(self) -> str:
        scope = f"[{self.scene}] " if self.scene else ""
        if self.status == "skipped":
            return f"[{self.id}] {scope}{self.title}：跳过——{self.detail}"
        measured = f"实测 {_fmt(self.value)} / 阈值 {_fmt(self.threshold)}"
        tail = f"；{self.detail}" if self.detail else ""
        return f"[{self.id}] {scope}{self.title}：{_fmt_status(self.status)}，{measured}{tail}"

    @property
    def failed(self) -> bool:
        return self.status == "fail"

    @property
    def warned(self) -> bool:
        return self.status == "warn"

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "scene": self.scene,
            "value": self.value,
            "threshold": self.threshold,
            "detail": self.detail,
        }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_status(status: str) -> str:
    return {"pass": "通过", "warn": "提醒", "fail": "失败", "skipped": "跳过"}.get(status, status)


#: 状态严重程度：同一幕多帧采样时取最严重的一条，避免把同一问题按帧重复计数。
#:
#: `skipped` 排在 `pass` **之下**（-1）：它不是一种严重程度，而是「这一帧没有可测的东西」。
#: 一幕的卡片在入场时还没出现、一幕的正文在某几帧还没入场，
#: 都不代表这一幕「没有卡片」「没有正文」。若把它排在任何实测结论之上，
#: 就会把已经量到的结论降级成「无法判定」——双栏对照的两张卡片在入场帧量不到，
#: 整幕于是报「没有可识别的卡片表面」，而画面上明明有卡片。
#: 只有**所有**采样帧都跳过时，才如实报「跳过」。
_SEVERITY = {"skipped": -1, "pass": 0, "warn": 2, "fail": 3}


@dataclass
class KeynoteResult:
    """全部闸门的结论集合。

    按「闸门 × 幕」聚合：逐帧采样会把同一个问题重复报好几遍，
    而按帧计数会让人误以为有很多问题。真实数值仍逐帧留在 `frames` 里，
    聚合条目保留最严重的那一份实测值与出现次数。
    """

    gates: list[Gate] = field(default_factory=list)
    frames: list[dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    reason: str = ""

    @property
    def ok(self) -> bool:
        return not any(gate.failed for gate in self.gates)

    def render(self, scene_id: str, frame: int, gates: list[Gate]) -> None:
        """记入一帧的逐条结论，并同步更新聚合条目。"""
        for gate in gates:
            gate.scene = gate.scene or scene_id
            self.frames.append({**gate.to_json(), "frame": frame})
            existing = next(
                (item for item in self.gates if item.id == gate.id and item.scene == gate.scene), None
            )
            if existing is None:
                aggregate = Gate(
                    id=gate.id,
                    title=gate.title,
                    status=gate.status,
                    value=gate.value,
                    threshold=gate.threshold,
                    detail=gate.detail,
                    scene=gate.scene,
                )
                aggregate.samples = 1  # type: ignore[attr-defined]
                self.gates.append(aggregate)
                continue
            existing.samples = getattr(existing, "samples", 1) + 1  # type: ignore[attr-defined]
            if _SEVERITY.get(gate.status, 0) > _SEVERITY.get(existing.status, 0):
                existing.status = gate.status
                existing.value = gate.value
                existing.threshold = gate.threshold
                existing.detail = gate.detail

    def summary(self) -> dict[str, int]:
        counts = {"pass": 0, "warn": 0, "fail": 0, "skipped": 0}
        for gate in self.gates:
            counts[gate.status] = counts.get(gate.status, 0) + 1
        return counts

    def to_json(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "reason": self.reason,
            "ok": self.ok,
            "summary": self.summary(),
            "gates": [
                {**gate.to_json(), "samples": getattr(gate, "samples", 1)} for gate in self.gates
            ],
            "frames": self.frames,
        }


# ---------------------------------------------------------------- 图像量测


def luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 相对亮度。"""
    channels = []
    for value in rgb:
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """WCAG 对比度，1.0–21.0。"""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _normalize_srgb_color(text: str) -> str:
    """把 `color(srgb r g b [/ a])` 折成 `rgb()` / `rgba()`。

    浏览器会把 `color-mix()` 算出来的底色序列化成这个形式（答案卡就是这么来的），
    而解析只认 `rgb()`/`rgba()`/`#hex`。不折的话解析失败会**静默退回画布**，
    量出 1.13 的假失败——假的之所以假，就因为它和「真的没有背景」长得一样。
    """
    if not text.startswith("color("):
        return text
    body = text[text.find("(") + 1 : text.rfind(")")]
    parts = body.replace("/", " ").split()
    if len(parts) not in (4, 5) or parts[0] != "srgb":
        return text
    try:
        channels = [round(float(part) * 255) for part in parts[1:4]]
    except ValueError:
        return text
    if len(parts) == 5:
        return f"rgba({channels[0]}, {channels[1]}, {channels[2]}, {parts[4]})"
    return f"rgb({channels[0]}, {channels[1]}, {channels[2]})"


def parse_color(value: str) -> tuple[int, int, int] | None:
    """解析 `rgb()` / `rgba()` / `#rrggbb` / `color(srgb …)`，解析不了返回 None。"""
    text = _normalize_srgb_color((value or "").strip().lower())
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        if len(digits) != 6:
            return None
        try:
            return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return None
    if text.startswith("rgb"):
        body = text[text.find("(") + 1 : text.rfind(")")]
        parts = [p.strip() for p in body.split(",")]
        if len(parts) < 3:
            return None
        try:
            return tuple(max(0, min(255, round(float(p)))) for p in parts[:3])  # type: ignore[return-value]
        except ValueError:
            return None
    return None


def parse_alpha(value: str) -> float:
    """取出颜色里的透明度；非 rgba 或解析不了按 1.0 处理。"""
    text = (value or "").strip().lower()
    if not text.startswith("rgb"):
        return 1.0
    body = text[text.find("(") + 1 : text.rfind(")")]
    parts = [p.strip() for p in body.split(",")]
    if len(parts) < 4:
        return 1.0
    try:
        return max(0.0, min(1.0, float(parts[3])))
    except ValueError:
        return 1.0


def composite(fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """把带透明度的前景压到背景上，得到实际显示出来的颜色。

    文字颜色常写成 `rgba(255,255,255,0.62)` 这种半透明值。直接拿它跟背景比
    会把「实际对比度」算高一大截，因此必须先合成再算。
    """
    return tuple(round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))  # type: ignore[return-value]


def rgb_metrics(rgb: bytes) -> dict[str, float]:
    """统计背景占比与强调色占比（需传入 108x192 的 RGB 原始数据）。"""
    total = len(rgb) // 3
    if not total:
        return {"empty": 0.0, "mean": 0.0}
    corner = (rgb[0], rgb[1], rgb[2])
    background = 0
    for index in range(0, len(rgb), 3):
        if (
            abs(rgb[index] - corner[0]) <= _BACKGROUND_TOLERANCE
            and abs(rgb[index + 1] - corner[1]) <= _BACKGROUND_TOLERANCE
            and abs(rgb[index + 2] - corner[2]) <= _BACKGROUND_TOLERANCE
        ):
            background += 1
    return {"empty": background / total}


def _hue(r: int, g: int, b: int) -> float:
    """返回 0–360 的色相（度）。三段线性，不引第三方色彩库。"""
    high = max(r, g, b)
    low = min(r, g, b)
    delta = high - low
    if delta == 0:
        return 0.0
    if high == r:
        return (60.0 * (((g - b) / delta) % 6)) % 360.0
    if high == g:
        return 60.0 * ((b - r) / delta + 2)
    return 60.0 * ((r - g) / delta + 4)


def accent_metrics(rgb: bytes, accent: tuple[int, int, int]) -> dict[str, float]:
    """统计强调色**族**的像素占比。

    判据是色度 + 色相，不是与某一个色值的逐通道差——理由见
    `_ACCENT_CHROMA_MIN`：色盒看不见设计系统登记的另外三个强调色成员。
    另附 `accent_pure` 作为诊断值（只含与纯强调色逐通道相差 ≤ 容差的像素），
    便于分辨「焦点是纯强调色画的」还是「用的是族里的暗档」。
    """
    total = len(rgb) // 3
    if not total:
        return {"accent": 0.0, "accent_pure": 0.0}
    accent_hue = _hue(*accent)
    hits = 0
    pure = 0
    for index in range(0, len(rgb), 3):
        r, g, b = rgb[index], rgb[index + 1], rgb[index + 2]
        if max(r, g, b) - min(r, g, b) < _ACCENT_CHROMA_MIN:
            continue
        delta = abs(_hue(r, g, b) - accent_hue)
        if min(delta, 360.0 - delta) > _ACCENT_HUE_TOLERANCE:
            continue
        hits += 1
        if (
            abs(r - accent[0]) <= _ACCENT_TOLERANCE
            and abs(g - accent[1]) <= _ACCENT_TOLERANCE
            and abs(b - accent[2]) <= _ACCENT_TOLERANCE
        ):
            pure += 1
    return {"accent": hits / total, "accent_pure": pure / total}


#: 可读墨迹的灰度下限。低于它的像素算背景（含渐变、光晕、点阵）。
_READABLE_LUMA = 120


def ink_metrics(rgb: bytes) -> dict[str, float]:
    """统计「足够亮、能读出来」的墨迹占比。

    作用与 `empty` 互补：`empty` 只看「有没有东西」，这一项看「东西读不读得出来」。
    标题常用渐变裁切绘制，计算样式的文字颜色是透明的，对比度闸门量不到它；
    用像素亮度补上这一格，避免「标题被调暗到几乎看不见」这类缺陷静默通过。
    """
    total = len(rgb) // 3
    if not total:
        return {"bright": 0.0}
    bright = 0
    for index in range(0, len(rgb), 3):
        luma = 0.2126 * rgb[index] + 0.7152 * rgb[index + 1] + 0.0722 * rgb[index + 2]
        if luma >= _READABLE_LUMA:
            bright += 1
    return {"bright": bright / total}


# ---------------------------------------------------------------- 闸门判定


def gate_whitespace(
    scene_id: str, scene_type: str, empty: float, bright: float | None = None
) -> Gate:
    """K1 留白预算：画面里有多少是「没有被内容占用」的像素。

    留白够但「亮到能读的墨迹」几乎为零，说明这一帧的文字被调暗到了看不见——
    这是渐变裁切标题最容易出的静默缺陷（对比度闸门量不到它）。
    """
    is_hero = scene_type in ("title", "quote", "conclusion")
    threshold = _EMPTY_MIN_QUOTE if is_hero else _EMPTY_MIN_DEFAULT
    if empty >= threshold:
        status = "pass"
    elif empty >= threshold - _EMPTY_WARN_MARGIN:
        status = "warn"
    else:
        status = "fail"
    hint = "留白不足会让画面显得拥挤，把它读成「层级不够」而不是「内容太多」"
    detail = f"{'主体' if is_hero else '信息'}幕门槛；{hint}" if status != "pass" else ""
    if status == "pass" and bright is not None and bright < _READABLE_MIN:
        status = "warn"
        detail = f"画面里亮到能读的墨迹只有 {bright:.4f}，文字可能被调暗到看不见"
    return Gate(
        id="K1",
        title="留白预算",
        status=status,
        value=round(empty, 4),
        threshold=threshold,
        detail=detail,
        scene=scene_id,
    )


def gate_accent(scene_id: str, accent: float) -> Gate:
    """K2 强调色占比：一个画面一个焦点，强调色用滥就等于没有焦点。

    判定是不对称的：强调色用滥是硬错误（焦点丢失），强调色偏少只是提醒。
    单个强调元素——一个重点词、一条焦点线、一个主角数字——本来就只有千分之几，
    把它判成失败会把大量正确画面拦下来。
    """
    if accent > _ACCENT_FAIL:
        status = "fail"
        detail = "强调色面积过大，视线失去了唯一落点"
    elif accent > _ACCENT_MAX:
        status = "warn"
        detail = "强调色面积偏大，检查是否出现了第二个焦点"
    elif accent >= _ACCENT_MIN:
        status = "pass"
        detail = ""
    elif accent >= _ACCENT_MIN / 2:
        status = "warn"
        detail = "强调色偏少，焦点不够明确"
    else:
        status = "warn"
        detail = "几乎没有强调色，画面缺一个焦点"
    return Gate(
        id="K2",
        title="强调色占比",
        status=status,
        value=round(accent, 4),
        threshold=[_ACCENT_MIN, _ACCENT_MAX],
        detail=detail,
        scene=scene_id,
    )


def gate_type_sizes(scene_id: str, sizes: list[float]) -> Gate:
    """K3 同帧字号种类：层级靠字号阶，不靠「稍微大一点」。"""
    distinct = sorted({round(size, 1) for size in sizes if size >= _TYPE_COUNT_FLOOR})
    if len(distinct) <= _MAX_TYPE_SIZES:
        status = "pass"
    elif len(distinct) <= _MAX_TYPE_SIZES + 1:
        status = "warn"
    else:
        status = "fail"
    return Gate(
        id="K3",
        title="同帧字号种类",
        status=status,
        value=distinct,
        threshold=f"≤{_MAX_TYPE_SIZES} 种（≥{_TYPE_COUNT_FLOOR}px 的层级字号）",
        detail="" if status == "pass" else "层级字号过多；应取自字号阶档位，而不是微调字号",
        scene=scene_id,
    )


def gate_alignment(scene_id: str, texts: list[dict[str, Any]], center: float | None = None) -> Gate:
    """K4 对齐基线：正文块应当落在少数几条对齐线上。

    只看「正文级」的文本块（字号 ≥ 44px）：图形里的标注、轴名、幕角标本来就
    画在各自的几何位置上，把它们算进来会把所有含图形的画面判成不对齐。

    判定用「对齐线数量」而不是「左边界极差」：居中构图与左对齐构图都是合法构图，
    居中构图下各块的左边界天然不同，用极差会把它误报成对不齐。做法是把每个文本块
    归到一条对齐线上——与安全区中心对齐的算「居中」这条线，其余按左边界聚类——
    线数超过两条才说明排布是散的。

    对称多栏构图同样合法：左右两栏的正文块各自向**本栏**的左边界对齐时，
    左边界必然相差一栏，但中心关于画面中心镜像，所以这种成对的线也并为一条。
    """
    blocks = [
        item
        for item in texts
        if float(item.get("fontSize") or 0) >= _ALIGN_MIN_FONT and item.get("left") is not None
    ]
    if len(blocks) < _ALIGN_MIN_SAMPLES:
        return Gate(
            id="K4",
            title="对齐基线",
            status="skipped",
            value=len(blocks),
            threshold=f"≤{_MAX_ALIGN_LINES} 条对齐线",
            detail="正文级文本块不足两个，无法判断对齐",
            scene=scene_id,
        )

    # 先按左边界聚类成「对齐线」，每条线记下代表左边界与该线上各块的**中心**
    centered = False
    groups: list[dict[str, Any]] = []
    for item in blocks:
        left = float(item["left"])
        item_center = float(item.get("center") or 0)
        if center and abs(item_center - center) <= _ALIGN_CENTER_TOLERANCE:
            centered = True
            continue
        for group in groups:
            if abs(left - group["left"]) <= _ALIGN_TOLERANCE:
                group["centers"].append(item_center)
                break
        else:
            groups.append({"left": left, "centers": [item_center]})

    # 互为镜像的两条线并成一条：左右两栏各自向本栏左边界对齐是正确做法，
    # 但左边界必然不同。判据是「两栏的块中心之和 ≈ 画面中心的两倍」。
    pairs: list[tuple[int, int]] = []
    paired: set[int] = set()
    if center:
        for i in range(len(groups)):
            if i in paired:
                continue
            for j in range(i + 1, len(groups)):
                if j in paired:
                    continue
                mirror = abs(groups[i]["centers"][0] + groups[j]["centers"][0] - 2 * center)
                if mirror <= _ALIGN_MIRROR_TOLERANCE:
                    pairs.append((i, j))
                    paired.update((i, j))
                    break

    lines: list[str] = []
    if centered:
        lines.append("居中")
    for index, group in enumerate(groups):
        if index in paired:
            continue
        lines.append(f"左 {round(group['left'])}")
    for i, j in pairs:
        lines.append(f"镜像对称（左 {round(groups[i]['left'])} / 左 {round(groups[j]['left'])}）")
    count = (1 if centered else 0) + (len(groups) - len(paired)) + len(pairs)
    status = "pass" if count <= _MAX_ALIGN_LINES else ("warn" if count == _MAX_ALIGN_LINES + 1 else "fail")
    return Gate(
        id="K4",
        title="对齐基线",
        status=status,
        value=count,
        threshold=f"≤{_MAX_ALIGN_LINES} 条对齐线",
        detail="" if status == "pass" else "正文块分散在多条对齐线上：" + "、".join(lines),
        scene=scene_id,
    )


def gate_contrast(
    scene_id: str,
    samples: list[dict[str, Any]],
    page_background: tuple[int, int, int] | None = None,
) -> Gate:
    """K5 正文对比度：令牌层面算出来的对比度，不含渐变与图形叠加。

    两类样本必须排除，否则会量出「假失败」：
    1. 渐变裁切绘制的标题——文字自身的颜色是透明的，真正显色的是背景裁切，
       前景色算出来是 `rgba(0,0,0,0)`，与背景的对比度恒为 1.0。
    2. 完全透明的文本节点（逐字动画拆出来的 span）——同理。
    背景为透明时回落到页面底色，因为画面里没有独立卡片底板。
    """
    worst_ratio: float | None = None
    worst_threshold = _CONTRAST_BODY
    worst_detail = ""
    for sample in samples:
        if sample.get("gradient"):
            continue
        alpha = parse_alpha(sample.get("color", ""))
        if alpha <= 0.02:
            continue
        fg = parse_color(sample.get("color", ""))
        # 背景归属：元素自己没涂色时，先看**最近一个被涂色的祖先**（卡片/面板），
        # 最后才回落到画布。少了这一步，卡片上的字会拿画布当背景——
        # 浅色主题下答案卡的白字因此量出 1.13:1 的假失败。
        bg_text = sample.get("background", "")
        if parse_color(bg_text) is None or parse_alpha(bg_text) <= 0.02:
            surface = sample.get("surface", "")
            if parse_color(surface) is not None and parse_alpha(surface) > 0.02:
                bg_text = surface
        bg = parse_color(bg_text)
        if bg is None or parse_alpha(bg_text) <= 0.02:
            bg = page_background
        if fg is None or bg is None:
            continue
        # 半透明文字要压到背景上再算，否则会把对比度算高一大截
        fg = composite(fg, alpha, bg)
        ratio = contrast_ratio(fg, bg)
        threshold = _CONTRAST_LARGE if sample.get("fontSize", 0) >= _LARGE_TEXT_PX else _CONTRAST_BODY
        if worst_ratio is None or ratio < worst_ratio:
            worst_ratio = ratio
            worst_threshold = threshold
            worst_detail = str(sample.get("role", "正文"))
    if worst_ratio is None:
        return Gate(
            id="K5",
            title="正文对比度",
            status="skipped",
            value=None,
            threshold={"正文": _CONTRAST_BODY, "大字": _CONTRAST_LARGE},
            detail="没有取到可计算的前景/背景色（文字可能压在渐变色或图形上）",
            scene=scene_id,
        )
    if worst_ratio >= worst_threshold:
        status = "pass"
    elif worst_ratio >= worst_threshold * 0.85:
        status = "warn"
    else:
        status = "fail"
    return Gate(
        id="K5",
        title="正文对比度",
        status=status,
        value=round(worst_ratio, 2),
        threshold=worst_threshold,
        detail="" if status == "pass" else f"{worst_detail} 的对比度低于下限",
        scene=scene_id,
    )


#: 卡片纪律：有卡片外观（圆角 > 8px 且有描边或阴影）时，必须同时具备
#: 圆角 + 1px 描边 + 阴影 + 顶部内高光中的至少三件，缺了就会显平。
_CARD_MIN_TRAITS = 3
_CARD_TRAITS = ("radius", "border", "shadow", "inset")


def gate_card_discipline(scene_id: str, cards: list[dict[str, Any]]) -> Gate:
    """K6 卡片纪律：卡片不能只画一个纯色块。

    采集范围是「整幕里所有被画出来的 HTML 表面」（见 `inspect._AESTHETIC_SCRIPT`），
    不只是图形挂载点的直接子元素——原先那样写，任何包在包装元素里的卡片都看不见，
    闸门会报「没有可识别的卡片表面」，而画面上明明有卡片。
    SVG 里的圆角矩形是图解对象，不是卡片，不在这里判。
    """
    if not cards:
        return Gate(
            id="K6",
            title="卡片与描边纪律",
            status="skipped",
            value=0,
            threshold=_CARD_MIN_TRAITS,
            detail="这一幕没有可识别的 HTML 卡片表面（SVG 里的圆角图形是图解对象，不算卡片）",
            scene=scene_id,
        )
    incomplete = [card for card in cards if len(card.get("traits") or []) < _CARD_MIN_TRAITS]
    status = "pass" if not incomplete else ("warn" if len(incomplete) == 1 else "fail")
    # 点名是哪几块表面缺项：只说「3 个表面缺少描边或阴影」，人无从下手改
    names = "、".join(f"「{_clip(card.get('role') or '表面')}」" for card in incomplete[:3])
    return Gate(
        id="K6",
        title="卡片与描边纪律",
        status=status,
        value=len(cards) - len(incomplete),
        threshold=f"{_CARD_MIN_TRAITS}/{len(_CARD_TRAITS)} 特征",
        detail="" if status == "pass" else f"{len(incomplete)} 个表面缺少描边或阴影，会显得扁平：{names}",
        scene=scene_id,
    )


#: 溢出判定允许的越界余量（px）。
#:
#: 入场动画会把文字整体位移，字幕级元素还有亚像素舍入，因此不能一有越界就报错；
#: 但也不能给太大——8px 在 1080 宽的画面里已经能看出来了，再多就不是舍入了。
_OVERFLOW_TOLERANCE = 8.0


def gate_overflow(
    scene_id: str,
    texts: list[dict[str, Any]],
    safe: dict[str, Any] | None,
    no_fit: list[dict[str, Any]] | None = None,
) -> Gate:
    """K7 文字溢出：文字不许越出安全区，缩到下限仍放不下就要拆场景。

    这是**硬判定**：文字被裁掉或压出安全区不是审美问题，是画面坏了。
    因此它和 K1–K6 那些「可以放行的提醒」不同，越界即 `fail`。

    两种情况一起看：像素/几何上真的越出了安全区，以及排版引擎已经算出
    「缩到正文下限仍放不下」——后者往往发生在越界之前，是更早的预警，
    但它同样意味着这一幕的文案必须拆开重写。
    """
    blocked = list(no_fit or [])
    if not safe:
        return Gate(
            id="K7",
            title="文字溢出",
            status="skipped",
            detail="取不到安全区几何，无法判定文字是否越界",
            scene=scene_id,
        )

    def overrun(text: dict[str, Any]) -> list[str]:
        parts = []
        if text.get("left", 0.0) < safe["left"] - _OVERFLOW_TOLERANCE:
            parts.append(("左", safe["left"] - text["left"]))
        if text.get("right", 0.0) > safe["right"] + _OVERFLOW_TOLERANCE:
            parts.append(("右", text["right"] - safe["right"]))
        if text.get("top", 0.0) < safe["top"] - _OVERFLOW_TOLERANCE:
            parts.append(("上", safe["top"] - text["top"]))
        if text.get("bottom", 0.0) > safe["bottom"] + _OVERFLOW_TOLERANCE:
            parts.append(("下", text["bottom"] - safe["bottom"]))
        return parts

    # 同一段落会被拆成多个文本节点（强调词、逐字揭示），按文本块归并：
    # 一段话越界只报一条，取该方向上最大的越界量。
    blocks: dict[str, dict[str, float]] = {}
    for text in texts:
        parts = overrun(text)
        if not parts:
            continue
        name = str(text.get("block") or text.get("role") or "文字")
        slot = blocks.setdefault(name, {})
        for side, amount in parts:
            slot[side] = max(slot.get(side, 0.0), amount)

    offenders = [
        f"「{_clip(name)}」" + "、".join(f"{side}越界 {amount:.1f}px" for side, amount in slot.items())
        for name, slot in blocks.items()
    ]

    if not offenders and not blocked:
        return Gate(
            id="K7",
            title="文字溢出",
            status="pass",
            value=0,
            threshold=f"越界 ≤ {_OVERFLOW_TOLERANCE:.0f}px",
            detail=f"量了 {len(texts)} 个文本块，都在安全区内",
            scene=scene_id,
        )

    detail_parts = []
    if offenders:
        detail_parts.append("越出安全区：" + "；".join(offenders[:4]))
    if blocked:
        names = "；".join(f"「{_clip(item.get('text') or '')}」" for item in blocked[:3])
        detail_parts.append(f"{len(blocked)} 段文案缩到正文下限仍放不下，需要拆场景：{names}")

    return Gate(
        id="K7",
        title="文字溢出",
        status="fail",
        value=len(offenders) + len(blocked),
        threshold=f"越界 ≤ {_OVERFLOW_TOLERANCE:.0f}px",
        detail="硬判定：" + "；".join(detail_parts),
        scene=scene_id,
    )


def _clip(value: Any, limit: int = 18) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


#: K8 容器内溢出的容差。比 K7 的 8px 小得多：入场动效会把整个图形分组一起
#: 平移与等比缩放，文字与容器的**相对**位置在这种变换下不变，
#: 剩下的只有亚像素舍入。留 2px 足够，再多就会把真正穿出去的文字放过去。
_CONTAINER_TOLERANCE = 2.0

#: 描边阶（与 keynote.css 的 `--a2v-stroke-*` 一致）。
_STROKE_LADDER = (1.0, 2.0, 3.0, 4.0, 6.0)

#: 同一帧允许出现的描边档数。超过就说明图形语言不成体系。
_MAX_STROKE_TIERS = 3


def gate_container_overflow(scene_id: str, inside: list[dict[str, Any]]) -> Gate:
    """K8 容器内溢出：图形内部的文字不许穿出它所属的容器。

    为什么需要单独一条，而不是靠 K7：K7 唯一的参照是 `.a2v-safe`，
    而图形内部的文字（飞轮节点、双向选择节点、冰山标注、天平载物、阶梯柱顶注）
    画在各自的几何位置上，`getComputedStyle` 量不到它们的排版盒，
    实测下来它们**既不受安全区判定、也不受容器判定**——完全在量程之外。

    后果是可见的：飞轮节点半径 76px（直径 152px），而节点标签在预设下是 44px，
    四个汉字带字距约 183px，比直径还宽 31px，文字必然穿出圆，
    而 K7 那时报的是「量了 2 个文本块，都在安全区内」。

    只检查**组件显式声明过容器**的文字（`data-a2v-inside` 指向容器选择器）：
    「这段文字是不是装在某个形状里」无法由几何自动判断——阶梯的注写在柱子**上方**，
    同样是近邻，却一点不装在里面。未声明的文字不在这里判定，
    但跳过要写明原因，不得算作通过。
    """
    threshold = f"越界 ≤ {_CONTAINER_TOLERANCE:.0f}px"
    if not inside:
        return Gate(
            id="K8",
            title="容器内溢出",
            status="skipped",
            threshold=threshold,
            detail="这一幕没有声明所属容器的图形文字，无法判定",
            scene=scene_id,
        )

    offenders: list[str] = []
    measured = 0
    worst = 0.0
    for item in inside:
        box = item.get("box") or {}
        shape = item.get("shape") or {}
        if not box or not shape:
            continue
        measured += 1
        if item.get("kind") == "circle":
            center_x = (float(shape["left"]) + float(shape["right"])) / 2
            center_y = (float(shape["top"]) + float(shape["bottom"])) / 2
            radius = (float(shape["right"]) - float(shape["left"])) / 2
            corners = (
                (float(box["left"]), float(box["top"])),
                (float(box["right"]), float(box["top"])),
                (float(box["left"]), float(box["bottom"])),
                (float(box["right"]), float(box["bottom"])),
            )
            amount = max(
                math.hypot(x - center_x, y - center_y) - radius for x, y in corners
            )
            where = "圆周"
        else:
            amount = max(
                float(shape["left"]) - float(box["left"]),
                float(box["right"]) - float(shape["right"]),
                float(shape["top"]) - float(box["top"]),
                float(box["bottom"]) - float(shape["bottom"]),
            )
            where = "容器边界"
        if amount <= _CONTAINER_TOLERANCE:
            continue
        worst = max(worst, amount)
        offenders.append(
            f"「{_clip(item.get('text'))}」穿出 {item.get('container') or '容器'}"
            f"（{where}）{amount:.1f}px"
        )

    if not offenders:
        return Gate(
            id="K8",
            title="容器内溢出",
            status="pass",
            value=0,
            threshold=threshold,
            detail=f"量了 {measured} 个声明了容器的图形文字，都在容器内",
            scene=scene_id,
        )

    return Gate(
        id="K8",
        title="容器内溢出",
        status="fail",
        value=round(worst, 1),
        threshold=threshold,
        detail="硬判定：" + "；".join(offenders[:4]),
        scene=scene_id,
    )


def gate_stroke_consistency(scene_id: str, widths: list[float]) -> Gate:
    """K9 图形描边一致性：同一帧的线宽要落在描边阶上，档数也要收敛。

    组件层原先散着 2 / 3 / 4 / 5 / 6 五种线宽，没有令牌、没有语义。
    苹果的图形语言是**少数几档线宽**；一屏里出现四五种线宽，
    观众说不出哪里不对，只会觉得「不够精致」——这正是最难自查的一类缺陷。

    只提示、不拦人：线宽不一致是观感问题，不是画面损坏。
    """
    if not widths:
        return Gate(
            id="K9",
            title="图形描边一致性",
            status="skipped",
            threshold=f"档数 ≤ {_MAX_STROKE_TIERS}，取值在描边阶上",
            detail="这一幕没有可量的描边",
            scene=scene_id,
        )
    rounded = sorted({round(width, 1) for width in widths if width > 0})
    off_ladder = [width for width in rounded if width not in _STROKE_LADDER]
    if off_ladder:
        return Gate(
            id="K9",
            title="图形描边一致性",
            status="warn",
            value=rounded,
            threshold=f"档数 ≤ {_MAX_STROKE_TIERS}，取值在描边阶上",
            detail=f"线宽 {off_ladder} 不在描边阶 "
            f"{[int(v) for v in _STROKE_LADDER]} 上；改用对应档位的令牌",
            scene=scene_id,
        )
    if len(rounded) > _MAX_STROKE_TIERS:
        return Gate(
            id="K9",
            title="图形描边一致性",
            status="warn",
            value=rounded,
            threshold=f"档数 ≤ {_MAX_STROKE_TIERS}，取值在描边阶上",
            detail=f"同一帧用了 {len(rounded)} 档线宽，图形语言不成体系",
            scene=scene_id,
        )
    return Gate(
        id="K9",
        title="图形描边一致性",
        status="pass",
        value=rounded,
        threshold=f"档数 ≤ {_MAX_STROKE_TIERS}，取值在描边阶上",
        detail="",
        scene=scene_id,
    )

