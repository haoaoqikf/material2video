from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "m2v.cli", "article", *args], cwd=ROOT,
                          text=True, capture_output=True, check=False,
                          encoding="utf-8", errors="replace", env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})


def test_input_review_candidate_and_explicit_adoption(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    article_dir = workspace / "videos" / "demo"
    article_dir.mkdir(parents=True)
    original = article_dir / "article.md"
    original_text = "原文观点。" * 100
    original.write_text(original_text, encoding="utf-8")
    args = ("--article", str(original), "--content-root", str(workspace))

    result = _run("input-review", *args)
    assert result.returncode == 0, result.stderr
    record_path = article_dir / "production.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["inputReview"]["lengthStatus"] == "fail"

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
    assert not (article_dir / "article.accepted.md").exists()

    result = _run("candidate", *args, "--text-file", str(candidate_file))
    assert result.returncode == 0, result.stderr
    result = _run("adopt-candidate", *args)
    assert result.returncode == 0, result.stderr
    accepted = article_dir / "article.accepted.md"
    assert accepted.is_file()
    assert original.read_text(encoding="utf-8") == original_text
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["inputReview"]["source"]["path"] == "videos/demo/article.accepted.md"
    assert record["inputReview"]["status"] == "pending"
    assert record["inputAdoption"]["candidate"]["path"] == "videos/demo/article.candidate.md"
    assert record["inputAdoption"]["accepted"]["path"] == "videos/demo/article.accepted.md"
    assert record["inputAdoption"]["confirmation"]["source"] == "explicit-user-adoption"

    candidate.write_text("再次采用的候选观点" * 16, encoding="utf-8")
    result = _run("adopt-candidate", *args)
    assert result.returncode == 0, result.stderr
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert (article_dir / "article.accepted.md").read_text(encoding="utf-8") == candidate.read_text(encoding="utf-8")
    assert record["inputAdoption"]["candidate"]["sha256"] == record["inputAdoption"]["accepted"]["sha256"]
    assert record["inputReview"]["status"] == "pending"


def test_blank_article_cannot_receive_a_fabricated_candidate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    article_dir = workspace / "videos" / "empty"
    article_dir.mkdir(parents=True)
    original = article_dir / "article.md"
    original.write_text(" \n，。\n", encoding="utf-8")
    args = ("--article", str(original), "--content-root", str(workspace))
    assert _run("input-review", *args).returncode == 0
    candidate_file = tmp_path / "candidate.md"
    candidate_file.write_text("无来源" * 50, encoding="utf-8")
    result = _run("candidate", *args, "--text-file", str(candidate_file))
    assert result.returncode == 2
    assert "不得编造候选稿" in result.stderr
    assert not (article_dir / "article.candidate.md").exists()
