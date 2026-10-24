"""共享手册的结构性契约：入口可达、链接可解析、命令与示例登记不缺失。

这里只检查「读者能否找到并打开」这类结构事实，不锁定正文措辞、小节标题或日期。
方法本身的正确性由制作与评审流程保证，改一个词不该让测试变红。
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1] / ".agents/skills/material2video/references"
REPO = ROOT.parents[3]


def test_visual_impact_reference_is_reachable_without_runtime_changes():
    """所有操作入口都指向同一份方法文档，且链接可解析。"""
    for name in ("production-workflow.md", "visual-creative-direction.md", "creative-production.md",
                 "scene-design-and-acceptance.md", "subagent-review.md", "director-review-and-edit.md",
                 "visual-review-rubric.md"):
        assert "visual-impact-design.md" in (ROOT / name).read_text(encoding="utf-8"), name
    for path in (ROOT.parent / "SKILL.md", REPO / "README.md", *REPO.glob("examples/*/DESIGN.md")):
        text = path.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+visual-impact-design\.md)\)", text)
        assert links, path
        assert all((path.parent / link).is_file() for link in links), path


def test_visual_creative_direction_is_reachable_from_every_entry():
    """视觉创意导演方法文档存在，并从制作、复核与示例入口可检索到。"""
    assert (ROOT / "visual-creative-direction.md").is_file()
    for name in ("production-workflow.md", "creative-production.md",
                 "article-to-storyboard.md", "scene-design-and-acceptance.md",
                 "visual-review-rubric.md", "director-review-and-edit.md"):
        assert "visual-creative-direction.md" in (ROOT / name).read_text(encoding="utf-8"), name
    assert "visual-creative-direction.md" in (ROOT.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "visual-creative-direction.md" in (REPO / "README.md").read_text(encoding="utf-8")


def test_fixed_examples_document_media_restore():
    """示例媒体不入库，两个有固定媒体的示例都必须写明恢复入口。"""
    root = REPO / "examples"
    for name in ("american-science-milestones", "solar-system-journey"):
        readme = (root / name / "README.md").read_text(encoding="utf-8")
        assert f"examples/{name}/assets/fetch.py" in readme, f"{name} 没有写明媒体恢复入口"
        assert (root / name / "assets/recipe.json").is_file()


def test_code_scene_contract_is_documented():
    """代码场景的公开入口与素材接入点在契约文档中可检索。"""
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    for token in ("m2v/code-scene", "subtitleSafeArea", "useMediaAsset"):
        assert token in schema, token


def test_reference_audio_reuse_is_documented():
    """参考音轨复用是受控例外：命令与授权开关必须在入口文档中出现。"""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "m2v ref audio" in readme and "--user-authorized" in readme
    skill = (ROOT.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "ref audio" in skill and "user-authorized" in skill
