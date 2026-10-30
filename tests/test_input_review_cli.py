from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.media


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "m2v.cli", "general", *args], cwd=ROOT,
                          text=True, capture_output=True, check=False,
                          encoding="utf-8", errors="replace", env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})


def _article_dir(workspace: Path, slug: str = "demo") -> Path:
    """文章归属固定为 videos/<类型>/<作品>/；旧的两层 videos/<作品>/ 不再推导得出。"""
    return workspace / "videos" / "general" / slug


def _write_project(article_dir: Path) -> None:
    """最小可用的 v8 作品：project.json、源文占位、本地场景入口与一份合法分镜。"""
    article_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "id": "demo-00000000",
        "type": "general",
        "materials": {"storyboard": "storyboard.json"},
        "output": {"width": 1920, "height": 1080, "fps": 60, "audio": "optional"},
    }
    (article_dir / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    board = {
        "version": 8, "schemaVersion": 8, "fps": 60, "width": 1920, "height": 1080, "title": "测试",
        "input": {"kind": "article"}, "targetSeconds": 60,
        "scenes": [{
            "id": "opening", "template": "code",
            "content": {"title": "观点", "entry": "scenes/opening.tsx"},
            "narrationSegments": [{"id": "line", "text": "旁白。"}],
        }],
    }
    (article_dir / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    entry = article_dir / "scenes/opening.tsx"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text((ROOT / "src/m2v/types/general/starters/scenes/opening.tsx").read_text(encoding="utf-8"),
                     encoding="utf-8")


def test_input_review_candidate_and_explicit_adoption(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    article_dir = _article_dir(workspace)
    _write_project(article_dir)
    original = article_dir / "article.md"
    original_text = "原文观点。" * 100
    original.write_text(original_text, encoding="utf-8")
    args = ("--storyboard", str(article_dir / "storyboard.json"))

    result = _run("input-review", *args)
    assert result.returncode == 0, result.stderr
    record_path = article_dir / "outputs" / "input-review.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    # 审查只记录源文摘要与非空计数，不再有 130～170 字的 lengthStatus 判定。
    assert record["schemaVersion"] == 5
    assert record["status"] == "pending"
    assert record["source"]["path"] == "article.md"
    assert record["charCount"] > 0

    candidate_file = tmp_path / "candidate.md"
    candidate_text = "候选观点" * 35
    candidate_file.write_text(candidate_text, encoding="utf-8")
    result = _run("candidate", *args, "--text-file", str(candidate_file))
    assert result.returncode == 0, result.stderr
    candidate = article_dir / "article.candidate.md"
    assert candidate.is_file()
    assert not (article_dir / "article.accepted.md").exists()
    assert original.read_text(encoding="utf-8") == original_text

    candidate.write_text("已被改动" * 35, encoding="utf-8")
    result = _run("adopt-candidate", *args)
    assert result.returncode == 2
    assert "已变化" in result.stderr
    assert not (article_dir / "article.accepted.md").exists()

    result = _run("candidate", *args, "--text-file", str(candidate_file))
    assert result.returncode == 0, result.stderr
    result = _run("adopt-candidate", *args)
    assert result.returncode == 0, result.stderr
    accepted = article_dir / "article.accepted.md"
    assert accepted.is_file()
    assert original.read_text(encoding="utf-8") == original_text
    # 采用候选稿会重开输入语义审查：采用不等于审查通过。
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["status"] == "pending"
    assert record["claim"] == "" and record["rationale"] == ""
    # 未显式声明 materials.article 的作品靠 article.accepted.md 自动作为当前源文。
    assert record["source"]["path"] == "article.accepted.md"
    manifest = json.loads((article_dir / "project.json").read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1 and manifest["type"] == "general"
    assert manifest["materials"] == {"storyboard": "storyboard.json"}


def test_blank_article_cannot_receive_a_fabricated_candidate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    article_dir = _article_dir(workspace, "empty")
    _write_project(article_dir)
    original = article_dir / "article.md"
    original.write_text(" \n，。\n", encoding="utf-8")
    args = ("--storyboard", str(article_dir / "storyboard.json"))
    # 空白源文连审查记录都生成不了：工具不替用户编造观点。
    result = _run("input-review", *args)
    assert result.returncode == 2
    assert "缺少非空源文" in result.stderr
    assert not (article_dir / "outputs" / "input-review.json").exists()
    candidate_file = tmp_path / "candidate.md"
    candidate_file.write_text("无来源" * 50, encoding="utf-8")
    result = _run("candidate", *args, "--text-file", str(candidate_file))
    assert result.returncode == 2
    assert "缺少非空原文" in result.stderr
    assert not (article_dir / "article.candidate.md").exists()
