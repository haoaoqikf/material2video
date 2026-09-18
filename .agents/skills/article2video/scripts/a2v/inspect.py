"""视觉体检：把「这条片子做对了没有」里能自动判定的部分跑一遍。

三件事，按可靠程度排序：

1. **契约探针**（确定性，最有力）：逐幕把帧停在收尾处，读出当前挂载点里
   每个 `data-el` 的文本，然后比对分镜声明的标注是否真的画出来了。
   这一条能抓住「画面照出、标签全空」这类静默缺陷——它不会报错，
   只有真的去读 DOM 才会发现。
2. **帧量测**（启发式）：逐帧统计墨迹覆盖率与上下安全区的墨迹，
   用于发现空幕、黑屏、内容压到边缘。
3. **设计宪法**（静态）：结构、曲线、模糊、挂载点、文案真源、安全区。
4. **观感闸门 K1–K9**（量测，可选）：启用设计语言预设时，量出留白预算、
   强调色占比、字号种类、对齐基线、正文对比度与卡片纪律。它与前三项**分开报告、
   分开计数**——前三项回答「这是不是废片」，K 系列回答「这像不像发布会级别的画面」。

评分与审美判断不在这里假装能做：`references/visual-review-rubric.md`
给出人工评审清单，本模块只负责把「需要人看的东西」都摆出来。
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imageio_ffmpeg import get_ffmpeg_exe

from . import catalog, constitution, keynote, motion
from .storyboard import Report

#: 采样点：入场后 / 中段 / 收尾。收尾那一帧同时用于契约探针。
SAMPLES = (0.35, 0.68, 0.96)

#: 量测用的缩略尺寸：够看出「哪里有多少墨」，又不至于在纯 Python 里逐像素太慢。
#: 强调色量测对分辨率敏感——108px 宽时一条 4px 的强调竖线会被混成接近背景的颜色，
#: 于是「画面里明明有强调色」被量成 0。540×960 是这条链路上的折中：
#: 细线不再被抹平，单帧解码仍在 0.3 秒量级。
_PROBE_W = 540
_PROBE_H = 960

#: 与画面主色调偏离多少灰度级才算「有墨」（渐变背景的浮动在 10 级以内）
_INK_DELTA = 40

#: 安全区：base.css 约定上 220px、下 320px（有字幕时再加 180px）
_SAFE_TOP_RATIO = 220 / 1920
_SAFE_BOTTOM_RATIO = 320 / 1920

#: 判定阈值：留得宽松，只抓明显问题，避免把正常画面判成失败
_MIN_INK = 0.004
_BAND_WARN = 0.05


@dataclass
class SceneProbe:
    """一幕的契约探针结果。"""

    scene_id: str
    frame: int
    kind: str
    declared_kind: str
    missing_labels: list[str] = field(default_factory=list)
    has_any_text: bool = True

    @property
    def ok(self) -> bool:
        return not self.missing_labels and self.has_any_text


#: 读出当前可见场景的组件结构：kind 与每个 data-el 的文本
_PROBE_SCRIPT = """
() => {
  var scenes = document.querySelectorAll('[data-a2v-scene]');
  var active = null;
  for (var i = 0; i < scenes.length; i++) {
    var style = window.getComputedStyle(scenes[i]);
    if (style.display !== 'none' && style.visibility !== 'hidden') { active = scenes[i]; break; }
  }
  if (!active) { return null; }
  var host = active.querySelector('[data-a2v-figure]');
  if (!host) { return { sceneId: active.getAttribute('data-scene-id'), kind: null, els: {} }; }
  var els = {};
  var nodes = host.querySelectorAll('[data-el]');
  for (var j = 0; j < nodes.length; j++) {
    var el = nodes[j];
    els[el.getAttribute('data-el')] = (el.textContent || '').replace(/\\s+/g, ' ').trim();
  }
  return {
    sceneId: active.getAttribute('data-scene-id'),
    kind: host.getAttribute('data-fig-kind'),
    els: els
  };
}
"""

#: 组件里表示「这里应该有字」的元素名后缀。读不到内容就值得看一眼。
#: 只用于文档说明：判定用的是「声明过的标注有没有出现」与「整幕是否全无文字」，
#: 逐个元素判空会误伤装饰性元素（例如用 CSS 画的箭头）。
_TEXT_SLOT = re.compile(r"(Text|Note|Label|Title|title|caption|action)$")


def decode_raw(png: bytes, pix_fmt: str) -> bytes:
    """把一帧缩到 108x192 的原始像素，用于逐像素统计。

    纯 Python 处理 2 万个像素是瞬时的，处理 200 万像素则不可接受；
    判断「哪里有多少墨、有多少强调色」不需要原始分辨率。
    """
    channels = 3 if pix_fmt == "rgb24" else 1
    completed = subprocess.run(
        [
            get_ffmpeg_exe(), "-v", "error", "-i", "pipe:0",
            "-vf", f"scale={_PROBE_W}:{_PROBE_H}",
            "-f", "rawvideo", "-pix_fmt", pix_fmt, "pipe:1",
        ],
        input=png,
        capture_output=True,
    )
    if completed.returncode != 0 or len(completed.stdout) != _PROBE_W * _PROBE_H * channels:
        raise ValueError("无法解码这一帧用于量测")
    return completed.stdout


def decode_gray(png: bytes) -> bytes:
    """灰度缩略图，用于墨迹覆盖率与安全区量测。"""
    return decode_raw(png, "gray")


def decode_rgb(png: bytes) -> bytes:
    """RGB 缩略图，用于留白率与强调色占比量测。"""
    return decode_raw(png, "rgb24")


def frame_metrics(gray: bytes) -> dict[str, float]:
    """统计墨迹覆盖率与上下安全区的墨迹。"""
    total = len(gray)
    values = sorted(gray)
    median = values[total // 2]
    top_rows = max(1, round(_SAFE_TOP_RATIO * _PROBE_H))
    bottom_start = _PROBE_H - max(1, round(_SAFE_BOTTOM_RATIO * _PROBE_H))

    ink = 0
    top_ink = 0
    bottom_ink = 0
    for index, value in enumerate(gray):
        if abs(value - median) <= _INK_DELTA:
            continue
        ink += 1
        row = index // _PROBE_W
        if row < top_rows:
            top_ink += 1
        elif row >= bottom_start:
            bottom_ink += 1
    return {
        "ink": ink / total,
        "band_top": top_ink / (top_rows * _PROBE_W),
        "band_bottom": bottom_ink / ((_PROBE_H - bottom_start) * _PROBE_W),
    }


def rgb_metrics(rgb: bytes) -> dict[str, float]:
    """留白率：与画面角落像素接近的像素占比，用于 K1 留白预算。"""
    return keynote.rgb_metrics(rgb)


def accent_metrics(rgb: bytes, accent: tuple[int, int, int]) -> dict[str, float]:
    """强调色面积占比，用于 K2。"""
    return keynote.accent_metrics(rgb, accent)


def ink_metrics(rgb: bytes) -> dict[str, float]:
    """亮到能读的墨迹占比，用于 K1 的「文字是否可见」自检。"""
    return keynote.ink_metrics(rgb)


def judge_frame(name: str, metrics: dict[str, float], report: Report) -> None:
    """按量测结果给出提示。阈值偏宽松，只抓明显问题。"""
    if metrics["ink"] < _MIN_INK:
        report.error(
            f"{name}#画面",
            f"整帧几乎没有内容（墨迹 {metrics['ink']:.2%}）：可能是组件没挂上、"
            "文案为空，或者画面全黑",
        )
    if metrics["band_top"] > _BAND_WARN:
        report.warn(
            f"{name}#安全区",
            f"顶部安全区内墨迹偏多（{metrics['band_top']:.1%}）："
            "顶部会被平台界面覆盖，重要内容请放低一些",
        )
    if metrics["band_bottom"] > _BAND_WARN:
        report.warn(
            f"{name}#安全区",
            f"底部安全区内墨迹偏多（{metrics['band_bottom']:.1%}）："
            "底部会被平台界面覆盖，重要内容请抬高一些",
        )


def judge_scene(probe: SceneProbe, labels: dict[str, str], report: Report) -> None:
    """契约探针的判定：声明了就必须真的画出来。"""
    where = f"场景 {probe.scene_id}#契约"
    if probe.declared_kind and probe.kind and probe.kind != probe.declared_kind:
        report.error(
            f"{where}",
            f"实际挂载的组件是 {probe.kind}，分镜声明的是 {probe.declared_kind}",
        )
    if not probe.kind:
        report.error(f"{where}", "这一幕没有挂载到任何组件，成片里会是一块空白")
        return
    if probe.missing_labels:
        report.error(
            f"{where}",
            "这些标注在整幕里都没有出现：「" + "」「".join(probe.missing_labels) + "」"
            "——组件挂上了但标签没画出来",
        )
    if not probe.has_any_text:
        report.error(f"{where}", "组件挂上了但整幕没有任何文字，确认不是漏了文案")
    if labels and not probe.kind:
        report.warn(f"{where}", "这一幕没有挂载点，声明了组件也不会画出来")


def probe_scene(page: Any, frame: int) -> dict[str, Any] | None:
    """把帧停住并读回当前场景的组件结构。"""
    page.seek(frame)
    return page.evaluate(_PROBE_SCRIPT)


def collect_labels(declared: dict[str, Any], seen_texts: set[str]) -> list[str]:
    """找出声明了但整幕都没出现在任何元素文本里的标注。

    比对的是「整幕所有采样帧里出现过的文本」，而不是某个元素最终的内容：
    翻转牌这类互换文案始终写进同一个元素，只看元素最后的值会漏判。
    """
    haystack = " ".join(sorted(seen_texts))
    missing: list[str] = []
    for key, value in declared.items():
        if not isinstance(value, str) or not value:
            continue
        if value not in haystack:
            missing.append(f"{key}={value}")
    return missing


def scene_labels(scene: dict[str, Any]) -> dict[str, str]:
    """分镜里这一幕声明的标注（figure.labels 优先，兼容旧的 annotations）。"""
    data = scene.get("data") or {}
    figure = data.get("figure") or {}
    labels = figure.get("labels") or data.get("annotations") or {}
    return {str(k): str(v) for k, v in labels.items() if isinstance(v, str)} if isinstance(labels, dict) else {}


def declared_kind(scene: dict[str, Any]) -> str:
    data = scene.get("data") or {}
    figure = data.get("figure") or {}
    kind = figure.get("kind") if isinstance(figure, dict) else None
    if isinstance(kind, str) and kind.strip():
        return kind.strip()
    return catalog.DEFAULT_KINDS.get(str(scene.get("type")), "")


def write_report(report: Report, extra: dict[str, Any], target: Path) -> dict[str, Any]:
    """把体检结果落成 report.json：给人和给下游自动修复用同一份。"""
    payload: dict[str, Any] = {
        "ok": report.ok,
        "errors": [issue.format() for issue in report.errors],
        "warnings": [issue.format() for issue in report.warnings],
        "summary": {
            "errors": len(report.errors),
            "warnings": len(report.warnings),
        },
    }
    payload.update(extra)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def check_page_with_storyboard(
    page_path: Path, scenes: list[dict[str, Any]], *, runtime_scenes: bool = False
) -> Report:
    """设计宪法的静态部分，并把分镜文案一起用于「单一真源」检查。

    `runtime_scenes` 表示这是共享页面，场景由它在运行时按分镜生成，
    依赖源码的检查项交给上面的运行时探针。
    """
    texts = constitution.storyboard_texts(scenes)
    return constitution.check_page(page_path, texts, runtime_scenes=runtime_scenes)


def scene_windows(scenes: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    """逐幕的绝对起止帧。

    分镜模型已经算好每幕的起始帧（启用配音后由媒体清单改写时长），
    因此优先用它；只有拿到裸 dict 时才自行累加。
    """
    cursor = 0
    windows: list[tuple[str, int, int]] = []
    for scene in scenes:
        length = int(scene.get("durationInFrames") or 0)
        start = int(scene.get("startFrame", cursor))
        windows.append((str(scene.get("id")), start, start + length))
        cursor = start + length
    return windows


def scenes_as_dicts(model: Any) -> list[dict[str, Any]]:
    """把分镜模型摊成体检需要的字段，避免这里再依赖模型内部结构。"""
    return [
        {
            "id": scene.id,
            "type": scene.type,
            "startFrame": scene.start_frame,
            "durationInFrames": scene.duration_in_frames,
            "data": scene.data,
        }
        for scene in model.scenes
    ]


def sample_frames(start: int, end: int) -> list[int]:
    """一幕内的采样帧：入场后 / 中段 / 收尾。"""
    span = max(end - start, 1)
    return [min(start + max(int(span * ratio), 1), end - 1) for ratio in SAMPLES]


def contact_sheet(frames: list[Path], target: Path, columns: int = 3) -> None:
    """把抽帧拼成一张联系表，便于一眼看完整支片子的节奏。"""
    if not frames:
        return
    listing = target.with_suffix(".txt")
    listing.write_text("\n".join(f"file '{path.as_posix()}'" for path in frames), encoding="utf-8")
    rows = (len(frames) + columns - 1) // columns
    try:
        subprocess.run(
            [
                get_ffmpeg_exe(), "-v", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(listing),
                "-vf", f"scale=360:640,tile={columns}x{rows}",
                "-frames:v", "1", str(target),
            ],
            check=True,
        )
    finally:
        listing.unlink(missing_ok=True)


def uses_component_library(page: Any) -> bool:
    """网页是否使用视觉组件库。

    不用组件库的网页（自己画图形）没有挂载点，契约探针无从谈起，
    此时应当明确跳过并说明，而不是逐幕报「未挂载」——那会把一个
    「没采用这套体系」误报成「画面是空白」。
    """
    return bool(page.evaluate("() => document.querySelectorAll('[data-a2v-figure]').length"))


#: 观感闸门要用的元素事实：每一帧在当前场景里读一次。
#: 只读计算样式与布局矩形，不做任何写操作，因此不会影响截图的确定性。
#:
#: 三类元素必须排除，否则闸门会误报：
#: 1. SVG 内的文字——它们画在各自的几何位置上，不是版式层级；`getComputedStyle`
#:    对 SVG 文本还会返回 `font-size: 36px` 这类祖先值，量出来没有意义。
#: 2. 装饰性字形（引号、下划线、逐字拆分的 span）——不是可读文本。
#: 3. 幕角标——它是画面 chrome，不参与构图对齐，字号也只有 caption 档。
_AESTHETIC_SCRIPT = """
() => {
  var scenes = document.querySelectorAll('[data-a2v-preset] [data-a2v-scene]');
  var active = null;
  for (var i = 0; i < scenes.length; i++) {
    var sceneStyle = window.getComputedStyle(scenes[i]);
    if (sceneStyle.display !== 'none' && sceneStyle.visibility !== 'hidden') { active = scenes[i]; break; }
  }
  if (!active) return null;

  var DECORATIVE = ['quote-mark', 'key-underline', 'reveal-char', 'a2v-scene-index', 'a2v-scene-number', 'a2v-scene-type'];
  var className = function (el) {
    if (!el || !el.className) return '';
    return String(el.className.baseVal !== undefined ? el.className.baseVal : el.className);
  };
  var isDecorative = function (el) {
    var cls = className(el);
    for (var d = 0; d < DECORATIVE.length; d++) {
      if (cls.indexOf(DECORATIVE[d]) >= 0) return true;
    }
    return false;
  };
  var isChrome = function (el) {
    return !!(el.closest && el.closest('.a2v-scene-index'));
  };
  // 行内容器：它们与所属文本块同进同退。越界要算在文本块上，否则一段话会被
  // 按文本节点重复计数，同一个问题报出三条。
  var INLINE_WRAPPERS = { key: 1, 'key-underline': 1, plain: 1 };
  var blockRole = function (el) {
    var node = el;
    while (node && node !== active && node.parentElement) {
      var names = className(node).split(/\\s+/).filter(Boolean);
      var wrapper = names.length > 0;
      for (var k = 0; k < names.length; k++) {
        if (!INLINE_WRAPPERS[names[k]]) { wrapper = false; break; }
      }
      if (!wrapper) break;
      node = node.parentElement;
    }
    return className(node) || String(node.tagName).toLowerCase();
  };

  var stage = document.querySelector('[data-a2v-preset] [data-a2v-stage]');
  var stageRect = stage ? stage.getBoundingClientRect() : { left: 0, width: 0 };
  var safeRect = active.querySelector('.a2v-safe');
  var safeBox = safeRect ? safeRect.getBoundingClientRect() : null;

  var sizes = [];
  var texts = [];
  var walker = document.createTreeWalker(active, NodeFilter.SHOW_TEXT, null);
  var text = walker.nextNode();
  while (text) {
    var parent = text.parentElement;
    if (parent && (text.textContent || '').trim()) {
      var isSvg = !!(parent.ownerSVGElement || String(parent.tagName).toLowerCase() === 'svg');
      var rect = parent.getBoundingClientRect();
      var style = window.getComputedStyle(parent);
      var visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      if (visible && !isSvg && !isChrome(parent)) {
        sizes.push(parseFloat(style.fontSize) || 0);
        if (!isDecorative(parent)) {
          var alpha = 1;
          var match = String(style.color).match(/rgba?\\(([^)]+)\\)/);
          if (match) {
            var parts = match[1].split(',');
            if (parts.length > 3) alpha = parseFloat(parts[3]);
          }
          texts.push({
            role: className(parent) || String(parent.tagName).toLowerCase(),
            block: blockRole(parent),
            fontSize: parseFloat(style.fontSize) || 0,
            left: Math.round(rect.left * 10) / 10,
            right: Math.round(rect.right * 10) / 10,
            top: Math.round(rect.top * 10) / 10,
            bottom: Math.round(rect.bottom * 10) / 10,
            center: Math.round((rect.left + rect.width / 2 - stageRect.left) * 10) / 10,
            color: style.color,
            // 标题常用「渐变裁切」绘制：文字自身的 color 是透明的，
            // 真正显色的是背景裁切。这类文本无法用前景色算对比度，
            // 标记出来让对比度闸门跳过，而不是量出 1.0 的假失败。
            gradient: (style.webkitBackgroundClip || style.backgroundClip) === 'text',
            alpha: isNaN(alpha) ? 1 : alpha,
            background: style.backgroundColor
          });
        }
      }
    }
    text = walker.nextNode();
  }

  // 卡片表面的采集范围：整幕里所有**被画出来的 HTML 表面**，而不只是图形挂载点的直接子元素。
  //
  // 原先只取 `[data-a2v-figure] > *`，于是任何包在包装元素里的卡片都看不见：
  // 双栏对照的两张卡片在 host > .vs-board > .vs-side 的深度 2，
  // 花费对照的两张在深度 3，闸门于是报「这一幕没有可识别的卡片表面」——
  // 而画面上明明有两张。这是**采集范围**的问题，不是阈值的问题，
  // 所以修的是范围，阈值（≥ 3 项特征）一个字没动。
  //
  // 两条边界：
  // 1. **SVG 图形不算卡片。** 天平载物、冰山标注、阶梯立柱都是圆角矩形，
  //    但它们只有圆角与描边——SVG 没有投影与内高光这回事，
  //    拿 HTML 卡片的四项特征去量必然"缺项"。它们是图解对象，
  //    图形纪律由 K9（描边一致性）与图形颜色预算测试管，不在这里判。
  // 2. **只判被画出来的表面。** 只判圆角会把透明的定位包装层算成卡片；
  //    必须有填充、边框或投影之一。宽度或高度不足 40px 的也不算——
  //    那是小徽标，不是能读成"一块表面"的东西。
  var cards = [];
  var cardHosts = [];
  var cardNodes = active.querySelectorAll('[data-a2v-figure] *');
  for (var j = 0; j < cardNodes.length; j++) {
    var el = cardNodes[j];
    var tag = String(el.tagName).toLowerCase();
    if (tag === 'rect' || tag === 'circle' || tag === 'ellipse' ||
        tag === 'path' || tag === 'polygon') continue;
    var s = window.getComputedStyle(el);
    var radius = parseFloat(s.borderTopLeftRadius) || 0;
    if (radius <= 8) continue;
    var borderWidth = parseFloat(s.borderTopWidth) || 0;
    var shadowText = s.boxShadow || 'none';
    var background = s.backgroundColor || '';
    var backgroundAlpha = 1;
    var bgMatch = background.match(/rgba?\\(([^)]+)\\)/);
    if (bgMatch) {
      var bgParts = bgMatch[1].split(',');
      if (bgParts.length > 3) backgroundAlpha = parseFloat(bgParts[3]);
    }
    var painted = backgroundAlpha > 0.02 || borderWidth > 0 || shadowText !== 'none';
    if (!painted) continue;
    var cardRect = el.getBoundingClientRect();
    if (cardRect.width < 40 || cardRect.height < 40) continue;
    // 最外层优先：卡片里的圆角徽标不再重复计一遍，否则一张卡会被数成两张
    var nested = false;
    for (var p = 0; p < cardHosts.length; p++) {
      if (cardHosts[p].contains(el)) { nested = true; break; }
    }
    if (nested) continue;
    var traits = ['radius'];
    if (borderWidth > 0) traits.push('border');
    if (shadowText !== 'none') traits.push('shadow');
    if (shadowText.indexOf('inset') >= 0) traits.push('inset');
    cardHosts.push(el);
    cards.push({ role: className(el) || tag, traits: traits });
  }

  var rootStyle = window.getComputedStyle(document.documentElement);
  // 缩到正文下限仍放不下的文本块：引擎已经算过，这里只把它捞出来
  var noFit = [];
  var fitNodes = active.querySelectorAll('[data-a2v-fit-fits="false"]');
  for (var n = 0; n < fitNodes.length; n++) {
    var node = fitNodes[n];
    var value = (node.textContent || '').replace(/\\s+/g, ' ').trim();
    if (value) noFit.push({ role: className(node) || String(node.tagName).toLowerCase(), text: value });
  }

  // 图形内部的文字：由组件显式声明「我装在哪个容器里」。
  // 「这段文字是不是装在某个形状里」无法由几何自动判断——阶梯的注写在柱子上方，
  // 同样是近邻，却一点不装在里面，所以只能由组件声明（data-a2v-inside 指向容器选择器）。
  // 坐标一律用 SVG 用户坐标（getBBox）：文字与容器同为同一个 <g> 的子节点，
  // 分组的入场变换对两者一致，相对关系不受影响。
  var inside = [];
  var insideNodes = active.querySelectorAll('[data-a2v-inside]');
  for (var q = 0; q < insideNodes.length; q++) {
    var label = insideNodes[q];
    var labelText = (label.textContent || '').replace(/\\s+/g, ' ').trim();
    if (!labelText) continue;
    var selector = label.getAttribute('data-a2v-inside');
    var scope = label.parentNode;
    var shape = scope && selector ? scope.querySelector(selector) : null;
    if (!shape) continue;
    try {
      var textBox = label.getBBox();
      var shapeBox = shape.getBBox();
    } catch (error) {
      continue;
    }
    if (!textBox.width || !shapeBox.width) continue;
    var shapeTag = String(shape.tagName).toLowerCase();
    inside.push({
      role: className(label) || String(label.tagName).toLowerCase(),
      text: labelText,
      container: selector,
      kind: shapeTag === 'circle' || shapeTag === 'ellipse' ? 'circle' : 'rect',
      box: {
        left: textBox.x,
        top: textBox.y,
        right: textBox.x + textBox.width,
        bottom: textBox.y + textBox.height
      },
      shape: {
        left: shapeBox.x,
        top: shapeBox.y,
        right: shapeBox.x + shapeBox.width,
        bottom: shapeBox.y + shapeBox.height
      }
    });
  }

  // 描边：同帧出现了几档线宽、取值在不在描边阶上。
  var strokes = [];
  var paintedNodes = active.querySelectorAll('svg *');
  for (var w = 0; w < paintedNodes.length; w++) {
    var painted = paintedNodes[w];
    var paintedStyle = window.getComputedStyle(painted);
    var strokeWidth = parseFloat(paintedStyle.strokeWidth) || 0;
    if (strokeWidth <= 0) continue;
    if (!paintedStyle.stroke || paintedStyle.stroke === 'none') continue;
    strokes.push(Math.round(strokeWidth * 10) / 10);
  }

  return {
    sizes: sizes,
    texts: texts,
    cards: cards,
    noFit: noFit,
    inside: inside,
    strokes: strokes,
    accent: rootStyle.getPropertyValue('--a2v-accent').trim(),
    background: rootStyle.getPropertyValue('--a2v-bg-0').trim(),
    center: safeBox ? safeBox.left + safeBox.width / 2 - stageRect.left : 0,
    safe: safeBox
      ? { left: safeBox.left, right: safeBox.right, top: safeBox.top, bottom: safeBox.bottom }
      : null,
    stage: { width: stageRect.width, height: stageRect.height }
  };
}
"""

#: 观感闸门的场景类型分组：主体幕（开场 / 金句 / 收束）有更高的留白门槛。
_HERO_SCENE_TYPES = ("title", "quote", "conclusion")


def keynote_gate(
    frame_name: str,
    scene_id: str,
    scene_type: str,
    rgb: bytes,
    facts: dict[str, Any] | None,
    accent: tuple[int, int, int] | None,
) -> list[keynote.Gate]:
    """把一帧的像素量测与元素事实转成一条条观感闸门结论。"""
    gates: list[keynote.Gate] = []
    background = rgb_metrics(rgb)
    gates.append(keynote.gate_whitespace(scene_id, scene_type, background["empty"], ink_metrics(rgb)["bright"]))
    if accent is None:
        gates.append(
            keynote.Gate(
                id="K2",
                title="强调色占比",
                status="skipped",
                detail="取不到主题的强调色令牌，无法量测强调色面积",
                scene=scene_id,
            )
        )
    else:
        gates.append(keynote.gate_accent(scene_id, accent_metrics(rgb, accent)["accent"]))

    if not facts:
        for gate_id, title in (
            ("K3", "同帧字号种类"),
            ("K4", "对齐基线"),
            ("K5", "正文对比度"),
            ("K6", "卡片与描边纪律"),
            ("K7", "文字溢出"),
            ("K8", "容器内溢出"),
            ("K9", "图形描边一致性"),
        ):
            gates.append(
                keynote.Gate(
                    id=gate_id,
                    title=title,
                    status="skipped",
                    detail="页面未启用设计语言预设，元素事实不可用",
                    scene=scene_id,
                )
            )
        return gates

    texts = facts.get("texts") or []
    page_background = keynote.parse_color(facts.get("background") or "")
    gates.append(keynote.gate_type_sizes(scene_id, list(facts.get("sizes") or [])))
    gates.append(
        keynote.gate_alignment(scene_id, texts, center=float(facts.get("center") or 0) or None)
    )
    gates.append(keynote.gate_contrast(scene_id, texts, page_background))
    gates.append(keynote.gate_card_discipline(scene_id, list(facts.get("cards") or [])))
    gates.append(
        keynote.gate_overflow(scene_id, texts, facts.get("safe"), list(facts.get("noFit") or []))
    )
    gates.append(keynote.gate_container_overflow(scene_id, list(facts.get("inside") or [])))
    gates.append(
        keynote.gate_stroke_consistency(
            scene_id, [float(width) for width in (facts.get("strokes") or [])]
        )
    )
    return gates


def run_inspect(
    page: Any,
    scenes: list[dict[str, Any]],
    frames_dir: Path,
    report_dir: Path,
    *,
    preset: str = "",
) -> tuple[Report, dict[str, Any]]:
    """在已打开的页面上跑完契约探针与帧量测，并落盘。"""
    report = Report()
    frames_dir.mkdir(parents=True, exist_ok=True)
    by_id = {str(scene.get("id")): scene for scene in scenes}
    probes: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    shots: list[Path] = []
    keynote_result = keynote.KeynoteResult(
        enabled=bool(preset),
        reason="" if preset else "该作品未启用设计语言预设（visual.preset），观感闸门不适用",
    )
    probing = uses_component_library(page)
    if not probing:
        report.warn(
            "页面#契约",
            "网页没有使用视觉组件库，已跳过组件契约探针；"
            "这一步是「标注是否真的画出来」的唯一检查手段",
        )

    for scene_id, start, end in scene_windows(scenes):
        scene = by_id.get(scene_id, {})
        expected_kind = declared_kind(scene)
        labels = scene_labels(scene)
        scene_type = str(scene.get("type") or "")
        frames = sample_frames(start, end)
        seen_texts: set[str] = set()
        last_els: dict[str, str] = {}
        mounted_kind = ""
        for index, frame in enumerate(frames):
            page.seek(frame)
            png = page.capture("png")
            target = frames_dir / f"{scene_id}-{int(SAMPLES[index] * 100):02d}-f{frame:04d}.png"
            target.write_bytes(png)
            shots.append(target)
            measured = frame_metrics(decode_gray(png))
            measured.update({"scene": scene_id, "frame": frame})
            metrics.append(measured)
            judge_frame(target.name, measured, report)

            if keynote_result.enabled:
                facts = page.evaluate(_AESTHETIC_SCRIPT)
                accent_text = (facts or {}).get("accent") or ""
                accent = keynote.parse_color(accent_text)
                keynote_result.render(
                    scene_id,
                    frame,
                    keynote_gate(target.name, scene_id, scene_type, decode_rgb(png), facts, accent),
                )

            # 顺带读一次组件结构：标注可能在幕内被替换（例如翻转牌），
            # 因此判定用的是整幕出现过的全部文本，而不是某一帧的瞬时状态
            if not probing:
                continue
            raw = page.evaluate(_PROBE_SCRIPT)
            if raw is None:
                continue
            mounted_kind = raw.get("kind") or mounted_kind
            last_els = raw.get("els") or last_els
            seen_texts.update(text for text in (raw.get("els") or {}).values() if text)

        probe = SceneProbe(
            scene_id=scene_id,
            frame=frames[-1],
            kind=mounted_kind,
            declared_kind=expected_kind,
            missing_labels=collect_labels(labels, seen_texts) if probing else [],
            has_any_text=bool(seen_texts) if probing else True,
        )
        judge_scene(probe, labels, report) if probing else None
        probes.append(
            {
                "scene": probe.scene_id,
                "frame": probe.frame,
                "kind": probe.kind,
                "declaredKind": probe.declared_kind,
                "labels": labels,
                "seenText": sorted(seen_texts),
                "lastFrameText": last_els,
                "missingLabels": probe.missing_labels,
                "ok": probe.ok,
            }
        )

    contact_sheet(shots, report_dir / "contact-sheet.png")
    # 动效量测放在抽帧之后：它要逐帧把页面再走一遍，量的是入场轨迹，
    # 与上面「抽若干帧看画面」互补——抽帧看不出「入场在幕内来不及落地」。
    motion_result = motion.audit(page, scenes)
    return report, {
        "contract": probes,
        "frames": metrics,
        "frameCount": len(shots),
        "usedComponentLibrary": probing,
        "keynote": keynote_result.to_json(),
        "motion": motion_result.to_json(),
    }
