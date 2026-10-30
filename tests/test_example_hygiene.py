"""示例与字体产物的版本控制卫生：生成媒体、缓存和字体二进制都不入库。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from example_catalog import EXAMPLE_PATHS

ROOT = Path(__file__).resolve().parents[1]


def test_nested_example_media_and_generated_files_stay_ignored() -> None:
    for root in EXAMPLE_PATHS.values():
        for relative in ('assets/media/check.png', 'assets/sound/check.wav',
                         'assets/sound-sources.json', 'outputs/check.json',
                         'article.candidate.md', 'article.accepted.md'):
            result = subprocess.run(['git', 'check-ignore', '--no-index', str(root / relative)],
                                    cwd=ROOT, capture_output=True)
            assert result.returncode == 0, f'{root.name}/{relative} 未被忽略'
    # 声音生成器和许可必须随示例目录继续入库。
    solar = EXAMPLE_PATHS['solar-system-journey']
    for name in ('generate.py', 'LICENSE.md'):
        result = subprocess.run(['git', 'check-ignore', '--no-index', str(solar / 'assets/sound' / name)],
                                cwd=ROOT, capture_output=True)
        assert result.returncode == 1


def test_no_generated_or_example_media_is_tracked() -> None:
    """成片、配音、预演与代码片段缓存都是派生产物；示例媒体按配方恢复，都不进版本控制。"""
    if shutil.which("git") is None:
        pytest.skip("环境里没有 git")
    listed = subprocess.run(["git", "ls-files", "styles", "fonts"], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            check=True).stdout.splitlines()
    generated = [name for name in listed
                 if "/outputs/" in name
                 or (name.endswith((".mp4", ".mov", ".webm", ".mp3")) and "/assets/media/" not in name)]
    restored = [name for name in listed
                if "/assets/media/" in name
                or ("/assets/sound/" in name and name.endswith((".wav", ".mp3")))]
    assert generated == [], f"示例里有生成媒体被跟踪：{generated}"
    assert restored == [], f"示例媒体应按 assets/fetch.py 恢复而非入库：{restored}"
    tracked_fonts = [name for name in listed if name.endswith((".ttf", ".otf", ".woff2"))]
    assert tracked_fonts == [], f"字体二进制应由 fonts/fetch.py 恢复而非入库：{tracked_fonts}"
    assert "fonts/registry.json" in listed, "字体登记表必须保留在版本控制中"
    assert any(name.startswith("fonts/licenses/") for name in listed), "字体许可必须保留在版本控制中"
