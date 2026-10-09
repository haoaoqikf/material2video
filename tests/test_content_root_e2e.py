"""内容根端到端：文章在仓库之外时，从分镜到成片整条路跑得通。

这是内容根功能的验收线：分镜与产物都在仓库之外，画面由仓库 `web/` 里的
契约页给出，两个根不同树，只能靠 `/__a2v_web__/` 别名接起来。

    产物必须落在内容根的 `videos/<slug>/outputs/` 下，溯源要能读回来（版本 3 + 别名页键），
否则「文章与仓库解耦」只是搬了个目录，验收时仍得回仓库里找。

需要 Chromium 与 ffmpeg，属于慢用例。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from a2v import cli, prepare as prep
from a2v.render import provenance_status
from conftest import approve_production_record

ROOT = Path(__file__).resolve().parents[1]
DECLARATIVE = ROOT / "examples/keynote-baseline/storyboard.json"

pytestmark = pytest.mark.slow


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    """仓库之外的内容根：`videos/demo/` 里放一份分镜。"""
    article = tmp_path / "content" / "videos" / "demo"
    article.mkdir(parents=True)
    shutil.copyfile(DECLARATIVE, article / "storyboard.json")
    scenes = article / "scenes"
    scenes.mkdir()
    shutil.copyfile(
        ROOT / "examples" / "keynote-baseline" / "scenes" / "option-map.tsx",
        scenes / "option-map.tsx",
    )
    media_path = prep.prepare(article / "storyboard.json", article / "outputs" / "media")
    # 发布闸门要求每份作品存在评审报告，且正式渲染需要 review.md 的全片节奏单项评分。
    outputs = article / "outputs" / "inspect"
    outputs.mkdir(parents=True)
    (outputs / "report.json").write_text(
        json.dumps(
            {"ok": True, "errors": [], "warnings": [], "aestheticReview": {"findings": []}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (outputs / "review.md").write_text(
        "# 视觉评审\n\n"
        "| 项 | 分 | 依据 |\n| --- | --- | --- |\n"
        "| 节奏 | 4 | 00:00 开场建立；00:01 核心动作推进后停留（内容根端到端测试夹具） |\n\n"
        "- 是否值得发布：通过\n- V6：通过\n- A6：通过\n",
        encoding="utf-8",
    )
    approve_production_record(article / "storyboard.json", media_path,
                              content_root=tmp_path / "content")
    return tmp_path / "content"


def test_declarative_render_writes_into_the_content_root(chromium_ready, content_root):
    """共享页面 + 内容根分镜：页面与分镜分处两个根，仍要渲得出来。"""
    assert cli.main_render(
        [
            "--storyboard", str(content_root / "videos" / "demo" / "storyboard.json"),
            "--content-root", str(content_root),
            "--media", str(content_root / "videos" / "demo" / "outputs" / "media" / "media.json"),
            "--limit-frames", "2",
            "--preset", "ultrafast",
            "--no-probe",
        ]
    ) == 0

    video = content_root / "videos" / "demo" / "outputs" / "previews" / "voiced.mp4"
    assert video.is_file() and video.stat().st_size > 0
    assert not (ROOT / "outputs" / "demo").exists(), "产物不得落回仓库"

    sidecar = json.loads(video.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    # version 4 起区分画面来源；默认路径由 Remotion composition 渲染。
    assert sidecar["version"] == 4
    assert sidecar["renderer"] == "remotion"
    # 产物在 videos/demo/outputs/previews/ 下：指回内容根要上四层
    assert sidecar["workspace"] == "../../../.."
    assert sidecar["page"] == "index.ts"
    assert sidecar["storyboard"] == "videos/demo/storyboard.json"
    assert "__a2v_web__/src/compositions/A2VComposition.tsx" in sidecar["assets"]["files"]
    # 下一页运行复核时不需要仓库标记、也不需要内容根参数
    assert provenance_status(video)["status"] == "current"


def test_environment_variable_alone_is_enough(chromium_ready, content_root, monkeypatch):
    """不传参数、只设 `A2V_CONTENT_ROOT` 时走同一条路。"""
    monkeypatch.setenv("A2V_CONTENT_ROOT", str(content_root))
    assert cli.main_render(
        [
            "--storyboard", str(content_root / "videos" / "demo" / "storyboard.json"),
            "--media", str(content_root / "videos" / "demo" / "outputs" / "media" / "media.json"),
            "--limit-frames", "2",
            "--preset", "ultrafast",
            "--no-probe",
        ]
    ) == 0
    assert (content_root / "videos" / "demo" / "outputs" / "previews" / "voiced.mp4").is_file()
