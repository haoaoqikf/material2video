"""生成原创 CC0 三列反馈记录图；运行后通过统一 assets import 导入。"""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright


def write() -> Path:
    root = Path(__file__).resolve().parents[3]
    font = base64.b64encode((root / 'web/src/assets/fonts/NotoSansSC-Variable.ttf').read_bytes()).decode()
    target = Path(__file__).resolve().parents[1] / 'outputs/generated/feedback.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [('第一次', '落点偏右上', '只改出手方向'), ('第二次', '偏差变小', '保持并再观察'), ('第三次', '更接近目标', '复查稳定性')]
    html = '<style>@font-face{font-family:local;src:url(data:font/ttf;base64,'+font+')}*{box-sizing:border-box}body{margin:0;background:#111720;color:#edf4fc;font-family:local;padding:55px 38px}h1{font-size:40px;margin:0 0 24px}p{font-size:26px;color:#a9b9cb}table{width:100%;border-collapse:collapse;font-size:27px}th,td{padding:30px 10px;text-align:left;border-bottom:2px solid #324459}th{color:#f7c85b;font-size:29px}</style>'
    html += '<h1>一轮尝试，留下三列记录</h1><p>预先明确目标：接近靶心</p><table><tr><th>轮次</th><th>实际观察</th><th>下次调整</th></tr>'
    html += ''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)
    html += '</table><p>示意记录 · 并非真实实验数据</p><p>结果未改善时，也要检查假设和停止条件。</p>'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':864,'height':800}, device_scale_factor=1)
        page.set_content(html)
        page.evaluate('document.fonts.ready')
        page.screenshot(path=str(target))
        browser.close()
    return target


if __name__ == '__main__':
    print(write())
