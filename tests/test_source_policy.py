from __future__ import annotations

import json
from pathlib import Path

from a2v import source_policy


def _scan(tmp_path: Path, name: str, source: str):
    web = tmp_path
    target = web / "src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    (web / "src/third-party").mkdir(parents=True, exist_ok=True)
    (web / "src/third-party/catalog.json").write_text("[]", encoding="utf-8")
    return source_policy.scan(web, [target])


def test_rejects_animation_library_entry(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "import {motion} from 'motion/react';")
    assert found and found[0].rule == "动画库入口"


def test_rejects_infinite_animation_utility(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "export const x = 'animate-spin infinite';")
    assert any(item.rule == "无限动画工具类" for item in found)


def test_rejects_unclassified_css_motion(tmp_path):
    found = _scan(tmp_path, "bad.css", ".x { transition: all 1s; animation: x 1s; } @keyframes x {}")
    assert sum(item.rule == "未适配的 CSS 动画/过渡" for item in found) == 3


def test_rejects_effect_timer(tmp_path):
    found = _scan(tmp_path, "Bad.tsx", "useEffect(() => { setInterval(step, 10); }, []);")
    assert any(item.rule == "计时器" for item in found)


def test_classified_css_requires_the_frame_wrapper(tmp_path):
    third = tmp_path / "src/third-party"
    third.mkdir(parents=True)
    source = third / "Demo.tsx"
    styles = third / "demo.css"
    source.write_text("export const Demo = () => null;", encoding="utf-8")
    styles.write_text("@keyframes x {} .x { animation: x 1s infinite; }", encoding="utf-8")
    (third / "catalog.json").write_text(json.dumps([{
        "id": "demo", "classification": "css-keyframes", "status": "representative",
        "source": "src/third-party/Demo.tsx", "styles": "src/third-party/demo.css"
    }]), encoding="utf-8")
    found = source_policy.scan(tmp_path, [])
    assert any(item.rule == "CSS 动画未经过帧同步包装" for item in found)


def test_repository_representative_is_allowed_and_classified():
    root = Path(__file__).resolve().parents[1]
    web = root / "web"
    from a2v import remotion

    assert source_policy.scan(web, remotion.build_inputs()) == []
    catalog = source_policy.load_catalog(web)
    assert {item["classification"] for item in catalog} == {"static", "css-keyframes", "clock"}
