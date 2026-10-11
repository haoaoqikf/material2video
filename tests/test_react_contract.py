"""渲染契约的错误诊断：版本、尺寸、帧率及总帧数不一致时明确拒绝。

旧版逐幕 DOM 页面断言已移除；v4 世界与阶段行为由前端 composition
集成测试及 test_inspect_v4_probe.py 覆盖。本文件保留无需浏览器的契约校验。
"""
from __future__ import annotations

import pytest

import m2v.engine.browser as browser
import m2v.engine.contract_page as contract_page
import m2v.types.article.render as render
from m2v.core.errors import M2VError


def _contract(fps: int = 30, frames: int = 180, width: int = 1080, height: int = 1920):
    return browser.PageContract(
        fps=fps, duration_in_frames=frames, width=width, height=height
    )


def _storyboard_like(fps: int = 30, frames: int = 180, width: int = 1080, height: int = 1920):
    import types

    return types.SimpleNamespace(
        fps=fps, total_frames=frames, width=width, height=height
    )


def test_rejects_a_page_that_does_not_declare_a_version():
    """旧页面（version 1）必须被明确拒绝，而不是等它在首帧截图上出问题。"""
    raw = {
        "ready": "function",
        "seek": "function",
        "version": None,
        "fps": 30,
        "durationInFrames": 180,
        "width": 1080,
        "height": 1920,
    }
    with pytest.raises(browser.BrowserError) as excinfo:
        browser._validate_contract(raw, "http://example.invalid/page.html")
    message = str(excinfo.value)
    assert "version" in message
    assert str(browser.CONTRACT_VERSION) in message


def test_rejects_a_page_with_the_wrong_version():
    raw = {
        "ready": "function",
        "seek": "function",
        "version": 1,
        "fps": 30,
        "durationInFrames": 180,
        "width": 1080,
        "height": 1920,
    }
    with pytest.raises(browser.BrowserError) as excinfo:
        browser._validate_contract(raw, "http://example.invalid/page.html", browser.CONTRACT_VERSION)
    message = str(excinfo.value)
    assert "1" in message and str(browser.CONTRACT_VERSION) in message


def test_fps_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_fps(_contract(fps=25), _storyboard_like(fps=30), None)
    message = str(excinfo.value)
    assert "25" in message and "30" in message


def test_dimension_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_dimensions(
            _contract(width=720, height=1280), _storyboard_like(width=1080, height=1920)
        )
    message = str(excinfo.value)
    assert "720" in message and "1280" in message
    assert "1080" in message and "1920" in message


def test_frame_count_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_total_frames(_contract(frames=150), _storyboard_like(frames=180))
    message = str(excinfo.value)
    assert "150" in message and "180" in message


def test_contract_page_missing_reports_how_to_build(tmp_path):
    """契约页不存在时要报出**构建命令**，而不是一句找不到文件。"""
    with pytest.raises(M2VError) as excinfo:
        contract_page.require_contract_page(tmp_path)
    message = str(excinfo.value)
    assert "pnpm" in message and "build" in message
