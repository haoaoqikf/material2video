"""Lucide 静态白名单在**构建产物**里的实测：只有白名单里的图标进了包。

规格（scene-primitive-tree）要求 `icon` 与 `pictogram` 只能引用受控白名单，
且**打包不引入全量图标**。校验器拦得住未知图标名，拦不住「打包器把整本图标
词典塞进 bundle」——后者不会报错，只会让每个页面白白多背几百 KB，
所以这里直接读构建产物验证。

依赖 `web/node_modules` 与 `web/dist`：两者任一不存在就跳过（与契约页实测同一口径）。
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "web/node_modules/lucide-react/dist/esm/icons"
BUNDLE_DIR = ROOT / "web/dist/contract/assets"
ICON_SET = ROOT / "web/src/primitives/iconSet.tsx"

#: 图标预算：白名单 14 个，再加少量余量给作品代码场景自带的图标。
#: 实测当前产物正好是白名单那 14 个——余量只是不让新增示例把测试变成假警报。
MAX_ICONS_IN_BUNDLE = 32

#: 与白名单无关的常见图标：它们出现就说明打包器没有按需引入。
UNRELATED = ("activity", "alarm-clock", "anchor", "banana", "bike", "cake", "cat", "compass")


def _skip_if_unbuilt() -> None:
    if not ICONS_DIR.is_dir():
        pytest.skip("未安装前端依赖：cd web && pnpm install")
    if not BUNDLE_DIR.is_dir():
        pytest.skip("未构建前端产物：cd web && pnpm build")


def _icon_marker(name: str) -> str:
    """图标在包里的精确标记：Lucide 的数据对象自带 kebab-case 名字。

    不用路径数据判断——短路径是长路径的子串（`M12 6v6` ⊂ `M12 6v6l4 2`），
    会把 `clock-12` 误判成 `clock`，实测多报十几个「进了包」的图标。
    """
    return f'name:"{name}"'


def _bundle_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(BUNDLE_DIR.glob("*.js")))


def _whitelist_icon_files() -> list[str]:
    """从 `iconSet.tsx` 的导入清单推出白名单对应的 Lucide 文件名。"""
    source = ICON_SET.read_text(encoding="utf-8")
    block = source[source.index("from 'lucide-react'"):source.index("ICON_SET:")]
    names = re.findall(r"\b([A-Z][A-Za-z0-9]*)\b", block)
    files = []
    for name in names:
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
        if (ICONS_DIR / f"{kebab}.mjs").is_file():
            files.append(kebab)
    return sorted(set(files))


def test_only_the_whitelist_is_bundled():
    _skip_if_unbuilt()
    bundle = _bundle_text()
    available = sorted(path.stem for path in ICONS_DIR.glob("*.mjs"))
    bundled = [name for name in available if _icon_marker(name) in bundle]
    assert len(bundled) < len(available) * 0.05, (
        f"包里出现了 {len(bundled)} / {len(available)} 个图标，按需引入没有生效：{bundled[:20]}"
    )
    assert len(bundled) <= MAX_ICONS_IN_BUNDLE, f"图标数量超出白名单规模：{bundled}"
    assert not set(UNRELATED) & set(bundled), f"与白名单无关的图标进了包：{sorted(set(UNRELATED) & set(bundled))}"


def test_every_whitelisted_icon_is_bundled():
    """白名单里的图标必须真的在包里：漏掉的话画面会空白，而校验器不会报错。"""
    _skip_if_unbuilt()
    bundle = _bundle_text()
    missing = [name for name in _whitelist_icon_files() if _icon_marker(name) not in bundle]
    assert not missing, f"白名单图标没有进包：{missing}"
