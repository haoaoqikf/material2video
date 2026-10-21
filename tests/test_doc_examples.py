"""通用手册描述当前 v8 全画布契约、真实时长与输入审查。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / ".agents/skills/material2video/references"


def test_workflow_and_compatibility_documented():
    text = (ROOT / "article-to-storyboard.md").read_text(encoding="utf-8")
    assert "确定画幅" in text and "视觉设计" in text and "不要求播放视频" in text
    assert "实际观看" not in text
    # 替代验收口径：查看帧序列与自动音频，不再把完整播放/试听写成完成前置。
    assert "帧序列" in text and "自动音频" in text
    assert "完整看听" not in text and "完整播放" not in text
    assert "候选稿须用户明确采用并重新审查后才能制作" in text
    assert "实际时长" in text and "600 秒" in text
    assert "最多3个" in text and "用户明确授权才可替换" in text
    assert "交通拥堵波按内容" in text and "traffic-jam-wave" in text
    assert "逐场设计与独立验收" in text and "百万播放潜力" in text
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    assert "v7 及更早分镜必须重新编排" in schema
    # v8 没有受控模板：画幅、配色与构图都由作品代码决定。
    assert 'template`（只能是 `code`）' in schema
    assert not any(kind in schema for kind in ("| point |", "| compare |", "| steps |", "| cause |"))


def test_media_and_sound_reference_documents_the_import_boundary():
    text = (ROOT / "article-media-and-sound.md").read_text(encoding="utf-8")
    assert "assets/media-sources.json" in text
    assert "assets/media/<sha256>" in text
    assert "useMediaAsset" in text and "未知" in text
    assert all(name in text for name in ["ding", "ding-dong", "click", "transition"])
    assert "M2V_PIXABAY_API_KEY" in text and "Pexels 固定停用" in text


def test_code_scene_contract_is_documented():
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    assert "m2v/code-scene" in schema and "outputs/code-cache/" in schema
    assert "subtitleSafeArea" in schema and "useMediaAsset" in schema
    assert "1920×1080" in schema and "1080×1920" in schema
    render = (ROOT / "code-scene-runtime.md").read_text(encoding="utf-8")
    assert "代码场景的顺序逐帧采集" in render and "契约页（`version: 6`）" in render
    assert "不使用 fps 重采样或尾帧复制" in render and "不支持倒序或跳帧" in render


def test_scene_design_and_reach_templates_are_documented():
    """逐场设计与独立验收、百万播放潜力都必须有可填写的模板与完成边界。"""
    scene = (ROOT / "scene-design-and-acceptance.md").read_text(encoding="utf-8")
    for token in ("逐场设计表", "多镜头场景表", "逐场验收表", "观察复述",
                  "填写演练", "不新增运行时", "缺项"):
        assert token in scene, f"逐场模板缺少：{token}"
    reach = (ROOT / "reach-potential.md").read_text(encoding="utf-8")
    for token in ("outputs/reach-potential-report.md", "支持具备潜力", "证据不足", "当前未达到",
                  "未知", "发布后验证", "演练", "保证播放量"):
        assert token in reach, f"潜力模板缺少：{token}"
    director = (ROOT / "director-review-and-edit.md").read_text(encoding="utf-8")
    for token in ("角色分离自审", "第一次导演审查", "第二次导演审查", "剪辑重组",
                  "回写", "重新 `prepare`", "全片否决", "真实观众", "判断演练"):
        assert token in director, f"导演审查模板缺少：{token}"
