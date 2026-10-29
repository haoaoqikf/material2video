"""生成《复利》独立目标静帧（S3 机制 / S5 规模与结果屏收束）。

静帧不是场景截图：这里用独立 HTML+SVG 按最终观感重新构图，供设计评审与手机
可读性检查。S5 的 result 只含表头与枚数；S6 是金顶归队的独立收束，establish 为
丘顶特写，result 为全白本金堆与结论片名。每个检查点按 establish/reveal/result
分别生成，写入 outputs/design/keyframes/，不纳入版本控制。
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / 'styles/examples/count-ledger/compound-interest'
OUT = EXAMPLE / 'outputs/design/keyframes'
FONT = ROOT / 'fonts/files/NotoSansSC-Variable.ttf'

BG = '#090B10'
OFF_WHITE = '#F1ECDD'
GOLD = '#EBC668'
DARK_GOLD = '#8A6E38'
MUTED = '#AAA99E'

HILL_ROWS = [26, 25, 24, 22, 20, 18, 16, 8]


def esc(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text(x: float, y: float, size: float, value: str, *, color: str = OFF_WHITE,
         anchor: str = 'start', weight: int = 500, opacity: float = 1) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" opacity="{opacity}">{esc(value)}</text>')


def disc(x: float, y: float, r: float, fill: str, *, opacity: float = 1, rim: str | None = None) -> str:
    highlight = (f'M{x - r * .64:.1f} {y - r * .44:.1f}'
                 f'a{r * .74:.1f} {r * .74:.1f} 0 0 1 {r * .92:.1f} {-r * .16:.1f}')
    parts = [
        f'<g opacity="{opacity}">',
        f'<ellipse cx="{x + r * .10:.1f}" cy="{y + r * .26:.1f}" rx="{r * .94:.1f}" '
        f'ry="{r * .86:.1f}" fill="#030407" opacity=".55"/>',
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}"/>',
        f'<path d="{highlight}" fill="none" stroke="#FFFFFF" stroke-opacity=".42" '
        f'stroke-width="{max(1, r * .05):.1f}"/>',
    ]
    if rim:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(1, r - 1.2):.1f}" fill="none" '
                     f'stroke="{rim}" stroke-width="{max(1, r * .05):.1f}" opacity=".55"/>')
    parts.append('</g>')
    return ''.join(parts)


def hill_positions(count: int, center: float, base: float) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for row, n in enumerate(HILL_ROWS):
        for i in range(n):
            if len(points) >= count:
                return points
            jitter_x = ((math.sin((row * 31 + i) * 12.9898) * 43758.5453) % 1) * 3 - 1.5
            jitter_y = ((math.sin((row * 17 + i) * 78.233) * 12345.6789) % 1) * 2 - 1
            if row == len(HILL_ROWS) - 1 and i == 4:
                jitter_x = jitter_y = 0
            points.append((center + (i - (n - 1) / 2) * 40 + jitter_x, base - row * 34 + jitter_y))
    return points


def s3_svg(phase: str = 'result') -> str:
    parts = []
    # establish 为 10 枚资本 + 首笔金色收益；reveal/result 为 11 枚 + 1.0/0.1 金。
    count = 10 if phase == 'establish' else 11
    for i in range(count):
        parts.append(disc(620, 930 - i * 64, 55, OFF_WHITE))
    parts.append(disc(660, 178, 55, GOLD, rim='#FFF4CF'))
    if phase != 'establish':
        parts.append(disc(760, 178, 55 * math.sqrt(.1), GOLD, rim='#FFF4CF'))
    parts.append(text(1120, 330, 72, '第 2 年', weight=600))
    parts.append(text(960, 1046, 54, '固定10%数学演示，非实际回报 · 不计税费及通胀',
                      color=MUTED, anchor='middle'))
    return ''.join(parts)


def s5_svg(phase: str = 'result') -> str:
    world = []
    # 左：40 枚整块。10 枚米白本金底排 + 30 枚暗金三排。
    for i in range(10):
        world.append(disc(300 + i * 42, 536, 21, OFF_WHITE))
    for i in range(30):
        world.append(disc(300 + (i % 10) * 42, 536 - (i // 10 + 1) * 42, 21, DARK_GOLD))
    # 右：158.631 枚资本丘 + 15.863 枚当年收益。
    points = hill_positions(159, 1360, 940)
    units = [1.0] * 158 + [.631]
    for (x, y), unit in zip(points, units):
        world.append(disc(x, y, 21 * math.sqrt(unit), OFF_WHITE))
    gold_units = [1.0] * 15 + [.863]
    for i, unit in enumerate(gold_units):
        x = 1360 + (i - (len(gold_units) - 1) / 2) * 40
        world.append(disc(x, 654, 21 * math.sqrt(unit), GOLD, rim='#FFF4CF'))

    parts = [f'<g transform="translate(960 540) scale(.925) translate(-960 -540)">'
             f'{"".join(world)}</g>']
    if phase in ('establish', 'reveal'):
        parts.append(text(120, 125, 60, '同样 10,000 · 同样 10% · 快进到第 30 年', color=MUTED))
    else:
        parts.append(text(120, 125, 60, '30 年后的总资产', color=MUTED))
    parts.append(text(500, 230, 60, '收益取走', anchor='middle', weight=600))
    parts.append(text(1360, 230, 60, '收益再投入', anchor='middle', weight=600))
    if phase == 'result':
        parts.append(text(500, 358, 84, '40 枚', anchor='middle', weight=600))
        parts.append(text(1360, 358, 88, '约 174.5 枚', color=GOLD, anchor='middle', weight=600))
    parts.append(text(960, 1012, 64, '固定10%数学演示，非实际回报 · 不计税费及通胀',
                      color=MUTED, anchor='middle'))
    return ''.join(parts)


def s6_svg(phase: str = 'result') -> str:
    """S6 金顶归队：establish 丘顶特写，reveal 全白全景，result 加结论与片名。"""
    world = []
    points = hill_positions(159, 1360, 940)
    units = [1.0] * 158 + [.631]
    for (x, y), unit in zip(points, units):
        world.append(disc(x, y, 21 * math.sqrt(unit), OFF_WHITE))
    gold_units = [1.0] * 15 + [.863]
    cap_y = 654 if phase == 'establish' else 680
    cap_fill = GOLD if phase == 'establish' else OFF_WHITE
    rim = '#FFF4CF' if phase == 'establish' else None
    for i, unit in enumerate(gold_units):
        x = 1360 + (i - (len(gold_units) - 1) / 2) * 40
        world.append(disc(x, cap_y, 21 * math.sqrt(unit), cap_fill, rim=rim))

    if phase == 'establish':
        transform = 'translate(960 540) scale(2) translate(-1360 -660)'
    else:
        transform = 'translate(960 540) scale(.95) translate(-1360 -540)'
    parts = [f'<g transform="{transform}">{"".join(world)}</g>']
    if phase != 'establish':
        parts.append(text(960, 1024, 64, '固定10%数学演示，非实际回报 · 不计税费及通胀',
                          color=MUTED, anchor='middle'))
    if phase == 'result':
        parts.append(text(960, 610, 80, '让收益，也成为本金。', color=GOLD, anchor='middle', weight=600))
        parts.append(text(960, 150, 112, '复利', anchor='middle', weight=600))
    return ''.join(parts)


def html(svg_body: str) -> str:
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><style>
@font-face {{ font-family: 'M2V Sans'; src: url('{FONT.as_uri()}') format('truetype'); }}
html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: {BG}; overflow: hidden; }}
svg {{ display: block; width: 100%; height: 100%; }}
text {{ font-family: 'M2V Sans', sans-serif; font-variant-numeric: tabular-nums; }}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 1920 1080">
<rect width="1920" height="1080" fill="{BG}"/>
{svg_body}
</svg></body></html>'''


def chrome() -> str:
    candidates = [
        os.environ.get('CHROME_PATH', ''),
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    found = shutil.which('chrome') or shutil.which('msedge')
    if not found:
        raise SystemExit('未找到 Chrome/Edge，可设置 CHROME_PATH')
    return found


def shoot(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page = OUT / f'{name}.html'
    page.write_text(html(body), encoding='utf-8')
    for width, height, suffix in [(1920, 1080, ''), (852, 479, '-852')]:
        target = OUT / f'{name}{suffix}.png'
        before = target.stat().st_mtime_ns if target.exists() else 0
        # Chrome 退出后仍可能短暂占用缓存文件；截图已完成，清理失败不应中断后续静帧。
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            user_data = Path(tmp) / 'profile'
            subprocess.run([
                chrome(), '--headless=new', '--disable-gpu', '--hide-scrollbars',
                # 管理员/服务进程拉起 Chrome 时，自动去提权会丢弃截图参数；显式关闭。
                '--do-not-de-elevate', '--no-first-run',
                '--force-device-scale-factor=1', f'--user-data-dir={user_data}',
                f'--window-size={width},{height}', '--virtual-time-budget=2500',
                f'--screenshot={target}', page.as_uri(),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Chrome 可能先返回、子进程随后才落盘；等到截图摘要稳定，避免 393 缩放读到旧图。
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if target.exists() and target.stat().st_mtime_ns != before:
                size = target.stat().st_size
                time.sleep(.2)
                if target.stat().st_size == size:
                    break
            time.sleep(.1)
        else:
            raise RuntimeError(f'等待 Chrome 截图超时：{target}')
    # Chrome 的窗口宽度有下限，393 宽按 852 实拍结果等比缩小。
    from imageio_ffmpeg import get_ffmpeg_exe
    subprocess.run([
        get_ffmpeg_exe(), '-v', 'error', '-i', str(OUT / f'{name}-852.png'),
        '-vf', 'scale=393:-1', '-frames:v', '1', '-y', str(OUT / f'{name}-393.png'),
    ], check=True)


if __name__ == '__main__':
    shoot('s3-establish', s3_svg('establish'))
    shoot('s3-reveal', s3_svg('reveal'))
    shoot('s3-mechanism', s3_svg('result'))
    shoot('s5-establish', s5_svg('establish'))
    shoot('s5-reveal', s5_svg('reveal'))
    shoot('s5-scale', s5_svg('result'))
    shoot('s6-establish', s6_svg('establish'))
    shoot('s6-reveal', s6_svg('reveal'))
    shoot('s6-scale', s6_svg('result'))
    for path in sorted(OUT.glob('*.png')):
        print(path.relative_to(ROOT))
