"""素材台账报告：登记、引用、许可与来源表的交叉核对。"""
from __future__ import annotations

import hashlib
import json

import pytest

from m2v.core.errors import M2VError
from m2v.engine import assets_tools
from helpers.scene_film import project


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record(root, entries):
    path = root / "assets/media-sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "assets": entries}, ensure_ascii=False),
                    encoding="utf-8")


def _asset(root, identity="a", *, data=b"fake-image", license="CC0", author="作者甲",
           source="https://example.com/a", path=None, sha=None, width=100, height=50):
    relative = path or f"assets/media/{_sha(data)}.jpg"
    if path is None:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"id": identity, "kind": "image", "path": relative, "width": width, "height": height,
            "sha256": sha or _sha(data), "sourceUrl": source, "author": author, "license": license}


def _scene(root, body="const asset = useMediaAsset(\"a\");"):
    path = root / "scenes/opening.tsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_complete_ledger_passes_without_claiming_audit(tmp_path):
    _record(tmp_path, [_asset(tmp_path)])
    _scene(tmp_path)
    (tmp_path / "SOURCES.md").write_text("| 用途 | 素材 ID |\n|---|---|\n| 开场 | `a` |\n",
                                         encoding="utf-8")
    report = assets_tools.build_report(tmp_path)
    assert report["status"] == "pass"
    assert report["summary"] == {"registered": 1, "referenced": 1, "errors": 0, "warnings": 1}
    assert report["assets"][0]["usage"]["status"] == "no-explicit-restriction"
    assert report["assets"][0]["sha256Matches"] is True
    assert report["assets"][0]["sourcesMentioned"] is True


def test_report_flags_unregistered_use_and_missing_sources_entry(tmp_path):
    _record(tmp_path, [_asset(tmp_path)])
    _scene(tmp_path, "const a = useMediaAsset(\"a\");\nconst b = useMediaAsset(\"ghost\");")
    report = assets_tools.build_report(tmp_path)
    assert report["status"] == "fail"
    codes = {item["code"] for item in report["problems"]}
    assert codes == {"used-not-registered"}
    assert report["unregistered"] == ["ghost"]
    warning_codes = {item["code"] for item in report["warnings"]}
    assert "sources-missing" not in warning_codes  # 作品没有 SOURCES.md 时不误报


def test_report_flags_unknown_license_and_tampered_file(tmp_path):
    _record(tmp_path, [_asset(tmp_path, license="未知", sha=_sha(b"other"))])
    _scene(tmp_path)
    report = assets_tools.build_report(tmp_path)
    codes = {item["code"] for item in report["problems"]}
    assert codes == {"sha-mismatch"}
    assert "license-unknown" in {item["code"] for item in report["warnings"]}


@pytest.mark.parametrize("usage,code", [
    ({"status": "prohibited"}, "usage-prohibited"),
    ({"status": "typo"}, "invalid-usage"),
])
def test_report_blocks_explicit_prohibition_and_invalid_metadata(tmp_path, usage, code):
    _record(tmp_path, [{**_asset(tmp_path), "usage": usage}])
    _scene(tmp_path)
    report = assets_tools.build_report(tmp_path)
    assert report["status"] == "fail"
    assert code in {item["code"] for item in report["problems"]}


def test_report_keeps_unmet_conditions_as_warning(tmp_path):
    _record(tmp_path, [{**_asset(tmp_path), "usage": {"status": "conditional", "conditionsMet": False}}])
    _scene(tmp_path)
    report = assets_tools.build_report(tmp_path)
    assert report["status"] == "pass"
    assert "usage-conditions-unmet" in {item["code"] for item in report["warnings"]}


def test_report_marks_dynamic_usage_and_unused_assets(tmp_path):
    _record(tmp_path, [_asset(tmp_path)])
    _scene(tmp_path, "const asset = useMediaAsset(id);")
    report = assets_tools.build_report(tmp_path)
    assert report["dynamicUsage"] is True
    assert report["unused"] == ["a"]
    codes = {item["code"] for item in report["warnings"]}
    assert {"unused", "dynamic-usage"} <= codes


def test_report_counts_wrapper_props_as_referenced(tmp_path):
    """包装组件把 ID 当 props 时，调用点只有变量；登记 ID 的字面量仍算引用。"""
    _record(tmp_path, [_asset(tmp_path)])
    _scene(tmp_path, "<Media id=\"a\" />")
    (tmp_path / "scenes/parts.tsx").write_text("const asset = useMediaAsset(id);", encoding="utf-8")
    report = assets_tools.build_report(tmp_path)
    assert report["assets"][0]["referenced"] is True
    assert report["unused"] == []
    assert all(item["code"] != "dynamic-usage" for item in report["warnings"])


def test_report_checks_explicit_sources_file(tmp_path):
    _record(tmp_path, [_asset(tmp_path)])
    _scene(tmp_path)
    sources = tmp_path / "SOURCES.md"
    sources.write_text("| 素材 |\n|---|\n| 无 |\n", encoding="utf-8")
    report = assets_tools.build_report(tmp_path, sources=sources)
    assert report["sources"]["missing"] == ["a"]
    assert any(item["code"] == "sources-missing" for item in report["warnings"])


def test_report_flags_entry_without_id(tmp_path):
    _record(tmp_path, [{"kind": "image", "path": "assets/media/x.jpg"}])
    report = assets_tools.build_report(tmp_path)
    assert report["status"] == "fail"
    assert any(item["code"] == "missing-id" for item in report["problems"])


def test_report_main_writes_json_and_returns_error_code(tmp_path):
    root, _ = project(tmp_path)
    _record(root, [_asset(root, path="assets/media/missing.jpg", sha=_sha(b"x"))])
    assert assets_tools.report_main(project=str(root), as_json=True) == 1
    saved = json.loads((root / "outputs/assets-report.json").read_text(encoding="utf-8"))
    assert saved["status"] == "fail"
    assert "不替代" in saved["notice"]


def test_report_main_rejects_missing_sources(tmp_path):
    root, _ = project(tmp_path)
    with pytest.raises(M2VError, match="来源表不存在"):
        assets_tools.report_main(project=str(root), sources=str(tmp_path / "nope.md"))
