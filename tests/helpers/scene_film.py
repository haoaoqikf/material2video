"""测试共用的项目夹具与构建入口。

这些函数原先散落在 ``test_article_explainer.py`` 与 ``test_code_scenes.py`` 里，
再由其他测试文件反向 import，导致测试之间互相耦合。集中到这里后，测试模块只依赖
本文件，不再依赖另一个测试模块。
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from m2v.core.project import create_project, load_project
from m2v.types.scene_film import explainer_review as review

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'templates/standalone/runtime/python'))
from film_runtime.engine import tts as local_tts  # noqa: E402
from film_runtime.types.scene_film import explainer_prepare as prepare  # noqa: E402
ENTRY = "scenes/opening.tsx"
STARTER = ROOT / "templates/standalone" / ENTRY
WEB = ROOT / "web"

requires_node = pytest.mark.skipif(
    shutil.which("node") is None or not (WEB / "node_modules" / "esbuild").is_dir(),
    reason="需要 Node 与前端依赖才能验证代码场景构建")


def scene(identity="a", **extra):
    body = {"id": identity, "template": "code",
            "content": {"title": "观点", "entry": ENTRY, "props": {"title": "观察反馈"}},
            "narrationSegments": [{"id": f"{identity}-line", "text": "观察结果，修正做法。"}]}
    body.update(extra)
    return body


def board(**extra):
    data = {"version": 9, "schemaVersion": 9, "fps": 60, "width": 1920, "height": 1080,
            "title": "测试", "input": {"kind": "article"}, "targetSeconds": 60,
            "scenes": [scene()]}
    data.update(extra)
    return data


def scene_root(path: Path) -> Path:
    """裸目录：契约校验只要求 entry 存在，不必先建整个作品。"""
    target = path / ENTRY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STARTER.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def project(tmp_path, data=None):
    root = tmp_path / "video"
    create_project(root, "text-motion", {"storyboard": "storyboard.json"})
    manifest_path = root / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output"]["fps"] = (data or board()).get("fps", 30)
    manifest["tts"] = {"voice": "zh-CN-YunxiNeural"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "storyboard.json").write_text(json.dumps(data or board(), ensure_ascii=False), encoding="utf-8")
    (root / "article.md").write_text("# 标题\n观察结果，根据反馈修正做法。", encoding="utf-8")
    (root / ENTRY).parent.mkdir(parents=True, exist_ok=True)
    (root / ENTRY).write_text(STARTER.read_text(encoding="utf-8"), encoding="utf-8")
    root, manifest = load_project(root)
    record = review.template(root, manifest)
    record.update(status="pass", claim="反馈帮助改进", rationale="原文有清晰观点和操作方法", reviewer="测试夹具")
    (root / "outputs").mkdir()
    (root / "outputs/input-review.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    (root / "fonts/files").mkdir(parents=True, exist_ok=True)
    for name in ("Inter-Variable.ttf", "NotoSansSC-Variable.ttf"):
        shutil.copy2(ROOT / "fonts/files" / name, root / "fonts/files" / name)
    return root, manifest


def fake_record(monkeypatch):
    """假录制：真实录制要构建前端并开浏览器，只有专门的用例才该承担。"""
    calls = []

    def record(root, target, inputs, *, frame, media, media_digest, capture_range=None, fps=30, jobs=1):
        path = root / "outputs/code-cache" / f"{target['id']}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"clip:" + target["id"].encode())
        entry = root / target["content"]["entry"]
        inputs["file:" + target["content"]["entry"]] = hashlib.sha256(entry.read_bytes()).hexdigest()
        inputs["codeMedia"] = media_digest
        relative = path.relative_to(root).as_posix()
        inputs["file:" + relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        calls.append({"scene": target["id"], "frame": frame, "media": media, "fps": fps})
        return relative

    digest_entry = lambda root, target, work: {
        "file:" + target["content"]["entry"]: hashlib.sha256((root / target["content"]["entry"]).read_bytes()).hexdigest()}
    monkeypatch.setattr(prepare.code_scenes.capture, "record", record)
    monkeypatch.setattr(prepare.code_scenes.capture, "build_scene", digest_entry)
    # 准备阶段直接调用包级 rebuild 入口收集可达依赖；它和录制内构建是两条路径。
    monkeypatch.setattr(prepare.code_scenes, "build_scene", digest_entry)
    return calls


def fake_tts(monkeypatch, seconds=1, samples=None):
    """假合成：可声明与落盘长度不同的时长，用于快速验证帧账本。"""
    calls = []

    def speak(text, voice, rate, cache, **kwargs):
        calls.append((text, voice, rate, kwargs))
        wav = cache / "fixture.wav"
        hit = wav.exists()
        import wave
        with wave.open(str(wav), "wb") as stream:
            stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            stream.writeframes(b"\x01\0" * round((seconds if samples is None else samples) * 24000))
        return wav, [{"start": 0, "end": seconds, "text": text}], [], seconds, hit

    monkeypatch.setattr(prepare.tts, "scene_audio", speak)
    monkeypatch.setattr(local_tts, "scene_audio", speak)
    return calls


def build(project_dir: Path, entry: str, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([shutil.which("node") or "node", str(WEB / "scripts/build-code-scene.mjs"),
                           str(project_dir), entry, str(output)], cwd=WEB, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=180)


def prepare_build(tmp_path: Path, source: str) -> tuple[Path, Path, subprocess.CompletedProcess[str]]:
    project_dir, output = tmp_path / "work", tmp_path / "out"
    (project_dir / "scenes").mkdir(parents=True)
    output.mkdir()
    (project_dir / "scenes/demo.tsx").write_text(source, encoding="utf-8")
    return project_dir, output, build(project_dir, "scenes/demo.tsx", output)


SOURCE = """import {motion, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {useEffect} from 'react';

export default function Demo({props}: CodeSceneProps) {
  const {ready, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  return <motion.div animate={running ? {opacity: 1} : {opacity: 0}}>{String(props.label ?? '演示')}</motion.div>;
}
"""


def code_scene(entry: str = "scenes/demo.tsx", props: object = None, **extra) -> dict:
    scene = {"id": "code-demo", "template": "code", "keywords": ["演示"],
             "content": {"title": "代码演示", "entry": entry, "props": {} if props is None else props},
             "narrationSegments": []}
    scene.update(extra)
    return scene


def write_source(root: Path, entry: str, source: str = SOURCE) -> None:
    file = root / entry
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


@contextmanager
def scene_page(tmp_path, source, *, frames=62, extra=None):
    import time
    from m2v.engine.http_server import LocalServer
    from playwright.sync_api import sync_playwright

    root, work, result = prepare_build(tmp_path, source)
    assert result.returncode == 0, result.stderr
    config = dict(props={}, fps=60, durationInFrames=frames, width=320, height=240,
                  segmentWindows={}, subtitleSafeArea=dict(x=0, y=200, width=320, height=40))
    config.update(extra or {})
    (work / 'index.html').write_text('<div id="root"></div><script>window.__M2V_CODE_CONFIG__='
                                    + json.dumps(config) + '</script><script src="scene.js"></script>', encoding='utf-8')
    with LocalServer(work, mounts={'/fonts': WEB / 'public/fonts'}, cors=True) as server, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 320, 'height': 240})
            page.add_init_script(path=str(WEB / 'src/code-scene/capture-clock.js'))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(server.base_url)
            deadline = time.monotonic() + 30
            while not page.evaluate('Boolean(window.__M2V_CODE__?.ready)'):
                assert not errors, errors
                assert time.monotonic() < deadline, '场景未就绪'
                page.evaluate('window.__M2V_CAPTURE_CLOCK__.bootstrap()')
            page.evaluate('window.__M2V_CODE__.start()')
            yield page, work
            assert not errors, errors
        finally:
            browser.close()
