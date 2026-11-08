"""验证真正生成到作品内的模板代码；不将主项目包注入被测子进程。"""
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / 'templates/standalone'
sys.path.insert(0, str(TEMPLATE / 'runtime/python'))
