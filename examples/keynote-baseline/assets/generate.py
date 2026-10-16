"""生成原创 CC0 路径筛选视频：多条候选、预算筛选、选定行动。"""
import base64
import subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright


def write() -> Path:
    root = Path(__file__).resolve().parents[3]
    font = base64.b64encode((root/'web/src/assets/fonts/NotoSansSC-Variable.ttf').read_bytes()).decode()
    out = Path(__file__).resolve().parents[1]/'outputs/generated'
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1080,'height':1920},device_scale_factor=1)
        for phase,title in enumerate(['先明确需要','按预算筛选','匹配时间，开始行动']):
            paths = ''
            for i,x in enumerate([190,420,660,890]):
                dim = phase>0 and i in (0,3)
                color = '#f7c85b' if phase==2 and i==2 else '#5aafff'
                paths += f'<g opacity="{0.15 if dim else 1}"><path d="M540 1250 L{x} 650" stroke="{color}" stroke-width="12"/><circle cx="{x}" cy="650" r="25" fill="{color}"/></g>'
            html = '<style>@font-face{font-family:local;src:url(data:font/ttf;base64,'+font+')}body{margin:0;background:#111720;color:#edf4fc;font-family:local}h1{text-align:center;font-size:54px;margin-top:180px}svg{position:absolute;top:0;left:0}p{position:absolute;top:1440px;width:100%;text-align:center;font-size:37px;color:#a9b9cb}</style>'
            labels = ''.join(f'<text x="{x}" y="560" text-anchor="middle" fill="#edf4fc" font-size="32">{label}</text>' for x,label in zip([190,420,660,890],['超预算','可行备选','时间合适','超预算'] if phase else ['候选一','候选二','候选三','候选四']))
            html += f'<h1>{title}</h1><svg width="1080" height="1920">{paths}{labels}<circle cx="540" cy="1250" r="28" fill="#f7c85b"/><text x="540" y="1350" text-anchor="middle" fill="#edf4fc" font-size="38">从当前需要出发</text></svg><p>候选 → 条件筛选 → 行动<br/><br/>原创示意 · 保留必要备选</p>'
            page.set_content(html)
            page.evaluate('document.fonts.ready')
            page.screenshot(path=str(out/f'phase-{phase}.png'))
        browser.close()
    command = [get_ffmpeg_exe(),'-y','-v','error']
    for i in range(3):
        command += ['-loop','1','-framerate','30','-t',str([5,5,10][i]),'-i',str(out/f'phase-{i}.png')]
    # 末段沿选中路径移动，前两段保留足够时间观察筛选结果。
    filters = r'[0:v][1:v][2:v]concat=n=3:v=1:a=0[bg];color=c=0xffe9a5:s=24x24:r=30:d=20[dot];[bg][dot]overlay=x=528+120*min(1\,(t-10)/4):y=1238-600*min(1\,(t-10)/4):enable=gte(t\,10):shortest=1'
    target = out/'choice.mp4'
    subprocess.run(command+['-filter_complex',filters,'-t','20','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    return target


if __name__ == "__main__":
    print(write())
