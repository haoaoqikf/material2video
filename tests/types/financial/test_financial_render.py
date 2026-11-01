"""金融导出：预演窗口、交付权限、初始化模板与 CLI 参数。"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from m2v.types.financial import financial
from m2v.engine import render_pipeline
from m2v.types.financial import financial_render
from m2v.core.errors import M2VError
from m2v.types.financial import commands as financial_video
from helpers.financial import edit, preview_fixture, project



def test_automatic_gate_does_not_require_preview(tmp_path):
    from m2v.types.financial.adapter import review_gate
    root = project(tmp_path)
    review_gate(root, {"materials": {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"}})




def test_full_preview_range_is_rejected(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    with pytest.raises(M2VError, match="不能覆盖全片"):
        financial_render.render(root, docs, preview=True, limit_frames=docs["plan"]["durationSeconds"] * 60)




def test_preview_cannot_overwrite_a_final_video(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    destination = root / "outputs/old-final.mp4"
    destination.parent.mkdir()
    destination.write_bytes(b"original final")
    with pytest.raises(M2VError, match="不能覆盖正式成片"):
        financial_render.render(root, docs, output=destination, preview=True)
    assert destination.read_bytes() == b"original final"




def test_preview_with_explicit_out_does_not_replace_the_recorded_preview(tmp_path, monkeypatch):
    """复核用的旁路预演 `--out` 不得顶掉已登记的完整预演，否则评审会静默失效。"""
    from types import SimpleNamespace

    import m2v.engine.remotion as remotion
    import m2v.engine.output_validation as output_validation

    root = project(tmp_path)
    docs = financial.load_project(root)
    preview_fixture(root, docs)
    record_path = root / "outputs/previews/preview-record.json"
    recorded = record_path.read_bytes()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(remotion, "web_dir", lambda: tmp_path)
    monkeypatch.setattr(remotion, "bundle", lambda **kwargs: SimpleNamespace(path=bundle, build_seconds=0.0,
        cache_seconds=0.0, cache_status="hit", cache_key="test", cache_detail="test"))
    monkeypatch.setattr(render_pipeline, "assert_no_audio", lambda video: None)
    monkeypatch.setattr(output_validation, "verify_output", lambda *args, **kwargs: None)
    def fake_session(**kwargs):
        render = kwargs["on_metadata"](SimpleNamespace(fps=60, width=1080, height=1920,
            duration_in_frames=docs["plan"]["durationSeconds"] * 60))
        Path(render["out"]).write_bytes(b"bypass preview")
        return {"readySeconds": 0.01}
    monkeypatch.setattr(remotion, "render_session", fake_session)

    output = financial_render.render(
        root, docs, preview=True, limit_frames=2, preset="ultrafast",
        output=root / "outputs/previews/verify-current-code.mp4",
    )
    assert output.read_bytes() == b"bypass preview"
    assert record_path.read_bytes() == recorded, "旁路预演不得改写已登记的预演记录"
    assert record_path.read_bytes() == recorded




@pytest.mark.parametrize("preview", [False, True])
def test_delivered_video_gets_inherited_access_after_being_moved(tmp_path, monkeypatch, preview):
    """交付文件必须重新继承父目录权限，且修复要在搬运之后、预演也一样。

    中转临时目录的 ACL 是刻意收紧的（只有 SYSTEM/Administrators/OWNER RIGHTS）。
    若在 temp 里就修复，`/reset` 只是把那份限制性 ACL 再套一遍；搬运后再 `/reset`
    才会继承 outputs 目录的可访问权限，否则标准权限播放器报 0x80070005。
    """
    from types import SimpleNamespace

    import m2v.engine.remotion as remotion
    import m2v.engine.output_validation as output_validation
    import m2v.core.security as security

    root = project(tmp_path)
    docs = financial.load_project(root)
    if not preview:
        from m2v.core.project import create_project, load_project
        from m2v.types.financial.adapter import prepare
        create_project(root, "financial-timeseries", {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"})
        _, manifest = load_project(root)
        prepare(root, manifest)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(remotion, "web_dir", lambda: tmp_path)
    monkeypatch.setattr(remotion, "bundle", lambda **kwargs: SimpleNamespace(path=bundle, build_seconds=0.0,
        cache_seconds=0.0, cache_status="hit", cache_key="test", cache_detail="test"))
    monkeypatch.setattr(render_pipeline, "assert_no_audio", lambda video: None)
    monkeypatch.setattr(output_validation, "verify_output", lambda *args, **kwargs: None)
    def fake_session(**kwargs):
        render = kwargs["on_metadata"](SimpleNamespace(fps=60, width=1080, height=1920,
            duration_in_frames=docs["plan"]["durationSeconds"] * 60))
        Path(render["out"]).write_bytes(b"video")
        return {"readySeconds": 0.01}
    monkeypatch.setattr(remotion, "render_session", fake_session)

    granted: list[Path] = []
    monkeypatch.setattr(security, "grant_inherited_access",
                        lambda path: granted.append(Path(path)) or True)

    output = financial_render.render(
        root, docs, preview=preview, limit_frames=2 if preview else None, preset="ultrafast",
    )
    assert output.is_file()
    assert output in granted
    assert all(path.is_file() for path in granted)




def test_init_creates_content_templates_for_a_stock_or_index(tmp_path, capsys):
    stock = tmp_path / "stock"
    assert financial_video.main([
        "init", "--out-dir", str(stock), "--kind", "stock", "--name", "合成公司",
        "--code", "SYN", "--display-name", "短名称", "--market", "TEST", "--unit", "USD", "--listing-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    assert all((stock / name).is_file() for name in financial.MATERIALS)
    stock_request = json.loads((stock / "request.json").read_text(encoding="utf-8"))
    assert stock_request["instrument"]["displayName"] == "短名称"
    assert stock_request["instrument"]["name"] == "合成公司"
    assert stock_request["instrument"]["code"] == "SYN"
    assert stock_request["investment"] == {"year": 2020, "principal": 100_000}
    stock_plan = json.loads((stock / "animation-plan.json").read_text(encoding="utf-8"))
    assert stock_plan["schemaVersion"] == 8 and stock_plan["canvas"] == {"width": 1080, "height": 1920}
    assert not (stock / "events.json").exists()
    index = tmp_path / "index"
    assert financial_video.main([
        "init", "--out-dir", str(index), "--kind", "index", "--name", "合成指数",
        "--code", "IDX", "--market", "TEST", "--unit", "points", "--index-start-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    index_request = json.loads((index / "request.json").read_text(encoding="utf-8"))
    assert index_request["instrument"]["indexStartDate"] == "2010-01-01"
    assert index_request["investment"] == {"year": 2020, "principal": 100_000}
    assert not (index / "events.json").exists()
    assert "初始化" in capsys.readouterr().out




def test_init_rejects_blank_display_name_without_creating_materials(tmp_path, capsys):
    output = tmp_path / "blank-name"
    assert financial_video.main([
        "init", "--out-dir", str(output), "--kind", "stock", "--name", "公司", "--code", "ABC",
        "--display-name", "  ", "--market", "TEST", "--unit", "USD", "--listing-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 2
    assert "--display-name 不能为空" in capsys.readouterr().err
    assert not output.exists()




@pytest.mark.slow
@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[3] / "web" / "node_modules").is_dir()
    or not shutil.which("node") or not shutil.which("npx"),
    reason="Remotion 前端依赖或 Node 未安装，无法执行金融视频端到端渲染",
)
def test_financial_preview_renders_widescreen_mp4_without_audio(tmp_path):
    root = project(tmp_path)
    # 从真实首个报价日开场，确保浏览器实际渲染非零居中位移下的折线并执行裁剪探针。
    # 空报价开场不会触发历史折线检查，曾使重复位移的裁剪错误漏过端到端测试。
    edit(root, "request.json", lambda data: data.update(displayRange=["2020-01-02", "2020-01-03"]))
    plan = financial.build_line_plan({"displayRange": ["2020-01-02", "2020-01-03"]}, duration=4)
    (root / "animation-plan.json").write_text(json.dumps(plan), encoding="utf-8")
    docs = financial.load_project(root)
    output = financial_render.render(root, docs, preview=True, limit_frames=2, preset="ultrafast")
    assert output.is_file() and output.stat().st_size > 0




@pytest.mark.parametrize("option", ["--window-months", "--window-months=12"])
def test_removed_window_argument_explains_staged_axis(option, capsys):
    with pytest.raises(SystemExit):
        financial_video.main(["plan", "--project-dir", "unused", option])
    assert "横轴按阶段扩展至完整日期范围" in capsys.readouterr().err