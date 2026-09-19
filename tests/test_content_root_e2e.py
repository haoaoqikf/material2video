"""内容根端到端：文章在仓库之外时，从分镜到成片整条路跑得通。

这是内容根功能的验收线。两种页面都要能渲出来：

* **共享页面**（声明式）：页面在仓库的 skill bundle 里、分镜在内容根里，
  两个根不同树，页面只能靠 `/__a2v__/` 别名提供；
* **专属页面**：页面与分镜同在内容根，靠静态根相对路径取。

产物必须落在内容根的 `outputs/<slug>/` 下，溯源要能读回来（版本 3 + 别名页键），
否则「文章与仓库解耦」只是搬了个目录，验收时仍得回仓库里找。

需要 Chromium 与 ffmpeg，属于慢用例。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from a2v import cli
from a2v.render import provenance_status

ROOT = Path(__file__).resolve().parents[1]
DECLARATIVE = ROOT / "examples/declarative-number/storyboard.json"
EXAMPLE_PAGE = ROOT / "examples/why-effort-fails/index.html"

pytestmark = pytest.mark.slow


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    """仓库之外的内容根：`videos/demo/` 里放一份分镜。"""
    article = tmp_path / "content" / "videos" / "demo"
    article.mkdir(parents=True)
    shutil.copyfile(DECLARATIVE, article / "storyboard.json")
    return tmp_path / "content"


def test_declarative_render_writes_into_the_content_root(chromium_ready, content_root):
    """共享页面 + 内容根分镜：页面与分镜分处两个根，仍要渲得出来。"""
    assert cli.main_render(
        [
            "--storyboard", str(content_root / "videos" / "demo" / "storyboard.json"),
            "--content-root", str(content_root),
            "--limit-frames", "2",
            "--preset", "ultrafast",
            "--no-probe",
        ]
    ) == 0

    video = content_root / "outputs" / "demo" / "previews" / "silent.mp4"
    assert video.is_file() and video.stat().st_size > 0
    assert not (ROOT / "outputs" / "demo").exists(), "产物不得落回仓库"

    sidecar = json.loads(video.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    # version 4 起区分画面来源；这条路径的画面来自网页
    assert sidecar["version"] == 4
    assert sidecar["renderer"] == "page"
    # 产物在 outputs/demo/previews/ 下：指回内容根要上三层
    assert sidecar["workspace"] == "../../.."
    assert sidecar["page"] == "__a2v__/declarative.html"
    assert sidecar["storyboard"] == "videos/demo/storyboard.json"
    assert "__a2v__/declarative.js" in sidecar["assets"]["files"]
    # 下一页运行复核时不需要仓库标记、也不需要内容根参数
    assert provenance_status(video)["status"] == "current"


def test_page_render_writes_into_the_content_root(chromium_ready, content_root):
    """专属页面 + 内容根分镜：页面在内容根里，静态根就是内容根。

    页面挪出仓库后相对引用就断了，共享资产必须改走 `/__a2v__/` 别名——这正是
    内容根里的文章页面的写法，因此这里按真实写法生成一份，别名那一侧也一起验。
    """
    article = content_root / "videos" / "demo"
    page_html = EXAMPLE_PAGE.read_text(encoding="utf-8").replace(
        "../../.agents/skills/article2video/assets/", "/__a2v__/"
    )
    assert "/__a2v__/timeline.js" in page_html
    (article / "index.html").write_text(page_html, encoding="utf-8")
    shutil.copyfile(
        ROOT / "examples/why-effort-fails/storyboard.json", article / "storyboard.json"
    )

    assert cli.main_render(
        [
            "--page", str(article / "index.html"),
            "--storyboard", str(article / "storyboard.json"),
            "--content-root", str(content_root),
            "--limit-frames", "2",
            "--preset", "ultrafast",
            "--no-probe",
        ]
    ) == 0

    video = content_root / "outputs" / "demo" / "previews" / "silent.mp4"
    assert video.is_file() and video.stat().st_size > 0
    sidecar = json.loads(video.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    assert sidecar["page"] == "videos/demo/index.html"
    assert sidecar["assets"]["files"]["videos/demo/index.html"]
    # 共享资产仍然记别名键：改组件库照样要能被发现
    assert any(key.startswith("__a2v__/") for key in sidecar["assets"]["files"])
    assert provenance_status(video)["status"] == "current"


def test_environment_variable_alone_is_enough(chromium_ready, content_root, monkeypatch):
    """不传参数、只设 `A2V_CONTENT_ROOT` 时走同一条路。"""
    monkeypatch.setenv("A2V_CONTENT_ROOT", str(content_root))
    assert cli.main_render(
        [
            "--storyboard", str(content_root / "videos" / "demo" / "storyboard.json"),
            "--limit-frames", "2",
            "--preset", "ultrafast",
            "--no-probe",
        ]
    ) == 0
    assert (content_root / "outputs" / "demo" / "previews" / "silent.mp4").is_file()
