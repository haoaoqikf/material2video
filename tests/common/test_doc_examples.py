"""共享手册的结构性契约：入口可达、链接可解析、命令与示例登记不缺失。

这里只检查「读者能否找到并打开」这类结构事实，不锁定正文措辞、小节标题或日期。
方法本身的正确性由制作与评审流程保证，改一个词不该让测试变红。
入口按阶段调度：专项文档默认不直接出现在 SKILL.md，但仍须能从入口经阶段指南与路由到达。
"""
from pathlib import Path
import json
import re

import pytest


ROOT = Path(__file__).resolve().parents[2] / ".agents/skills/material2video/references"
SKILL = ROOT.parent / "SKILL.md"
REPO = ROOT.parents[3]


def reachable() -> dict[str, Path]:
    """从 SKILL.md 沿活动链接与阅读路由可达的参考文档；不含模板围栏内的示例链接。"""
    seen: dict[str, Path] = {}
    route = json.loads((ROOT / "guidance-routes.json").read_text(encoding="utf-8"))
    queue = [SKILL]
    queue += [(ROOT / row["guide"]).resolve()
              for key in ("stages", "tasks", "conditional") for row in route[key]]
    queue += [(ROOT / value).resolve() for key in ("types", "ruleOwners") for value in route[key].values()]
    while queue:
        path = queue.pop().resolve()
        if not path.is_file() or path.name in seen:
            continue
        seen[path.name] = path
        if path.suffix != ".md":
            continue
        text = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", path.read_text(encoding="utf-8"), flags=re.S | re.M)
        for reference in re.findall(r"\]\(([^)\n]+)\)", text):
            if "://" in reference or reference.startswith("mailto:"):
                continue
            target = (path.parent / reference.partition("#")[0]).resolve()
            if target.is_file():
                queue.append(target)
    return seen


def test_reference_docs_are_reachable_from_the_entry():
    """专项方法文档可从入口经阶段指南与路由到达。"""
    docs = reachable()
    for name in ("visual-creative-direction.md", "reference-video-analysis.md",
                 "article-media-and-sound.md", "visual-review-rubric.md", "stage-plan.md",
                 "stage-iterate.md", "stage-final.md", "checkpoint-gates.md"):
        assert name in docs, name


@pytest.mark.parametrize("name,documents", [
    ("visual-creative-direction.md", ("production-workflow.md", "creative-production.md",
                                      "stage-plan.md", "subagent-review.md",
                                      "director-review-and-edit.md", "visual-review-rubric.md")),
    ("reference-video-analysis.md", ("reference-style.md", "creative-production.md",
                                     "visual-creative-direction.md", "subagent-review.md")),
])
def test_methods_are_linked_from_the_operating_docs(name, documents):
    """创作方法和参考拆解从相关操作文档可达。"""
    for document in documents:
        text = (ROOT / document).read_text(encoding="utf-8")
        assert name in text, f"{document} 没有指向 {name}"


def test_readme_and_example_links_resolve():
    """README 与风格示例的设计文档仍须有可打开的创作方法链接。"""
    name = "visual-creative-direction.md"
    paths = (REPO / "README.md", *REPO.glob("styles/*/examples/*/DESIGN.md"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        links = re.findall(rf"\]\(([^)]+{re.escape(name)})\)", text)
        assert links, f"{path} 没有指向 {name}"
        assert all((path.parent / link).is_file() for link in links), path


def test_fixed_examples_document_media_restore():
    """风格示例媒体不入库，两个有固定媒体的示例都必须写明恢复入口。"""
    root = REPO / "styles"
    for style, name in (("doc-archive", "american-science-milestones"),
                         ("deep-journey", "solar-system-journey")):
        readme = (root / style / "examples" / name / "README.md").read_text(encoding="utf-8")
        assert f"styles/{style}/examples/{name}/assets/fetch.py" in readme, f"{name} 没有写明媒体恢复入口"
        assert (root / style / "examples" / name / "assets/recipe.json").is_file()

