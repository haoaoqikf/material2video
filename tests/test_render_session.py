"""同一 Node 会话里的元数据握手与浏览器复用。

对应 openspec 变更 `optimize-final-video-render` 的任务 3.2。
这些用例不需要 Remotion：会话协议是 Python 与 Node 之间的**行协议**，
用一个内联的 Node 脚本就能把「沉默、EOF、失败、取消、拒绝确认」全部造出来，
包括验证进程树在每种收场下都被收掉。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import m2v.engine.remotion as remotion

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="需要 Node 才能验证会话协议"
)

METADATA = {"id": "TestComposition", "fps": 60, "width": 1080, "height": 1920, "durationInFrames": 90}


def _js_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _spawn_with(script: str, *, record: list | None = None):
    """把 `_spawn` 换成跑一段内联 Node 脚本，命令本身不做验证。"""

    def spawn(command, cwd, *, stdin):
        process = subprocess.Popen(
            [remotion.program("node"), "-e", script],
            cwd=str(cwd),
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if record is not None:
            record.append(process)
        return process

    return spawn


def _handshake_script(
    tmp_path: Path,
    *,
    metadata: dict | None = None,
    session: dict | None = None,
    ready: bool = True,
    confirm_exit: int = 0,
    confirm_output: str = "remotion-render: 渲染失败",
    hang_after_metadata: bool = False,
) -> str:
    """一段只实现协议的假渲染脚本：所有行为都由参数决定。"""
    meta = json.dumps(metadata or METADATA)
    sess = json.dumps(session or {"browsersOpened": 1, "compositionId": "TestComposition"})
    confirm_file = _js_path(tmp_path / "confirm.json")
    abort_file = _js_path(tmp_path / "abort.json")
    render_file = _js_path(tmp_path / "render.txt")
    lines = [
        "const fs = require('fs');",
        f"process.stdout.write('{remotion.SESSION_PREFIX}' + {json.dumps(sess)} + '\\n');",
        f"process.stdout.write('{remotion.METADATA_PREFIX}' + {json.dumps(meta)} + '\\n');",
    ]
    if ready:
        lines.append(f"process.stdout.write('{remotion.READY_PREFIX}\\n');")
    if hang_after_metadata:
        # 保持进程存活但什么都不做：Python 侧必须自己超时
        lines.append("setInterval(() => {}, 1000);")
        return "\n".join(lines)
    lines += [
        "let buf = '';",
        "process.stdin.on('data', (chunk) => {",
        "  buf += chunk.toString('utf8');",
        "  const index = buf.indexOf('\\n');",
        "  if (index < 0) return;",
        "  const line = buf.slice(0, index);",
        f"  if (line.startsWith('{remotion.ABORT_PREFIX}')) {{ fs.writeFileSync('{abort_file}', line); process.exit(3); }}",
        f"  if (line.startsWith('{remotion.CONFIRM_PREFIX}')) {{",
        f"    fs.writeFileSync('{confirm_file}', line.slice({len(remotion.CONFIRM_PREFIX)}));",
    ]
    if confirm_exit:
        lines += [
            f"    process.stderr.write({json.dumps(confirm_output)} + '\\n');",
            f"    process.exit({confirm_exit});",
        ]
    else:
        lines += [
            f"    process.stdout.write('{remotion.PROGRESS_PREFIX}50\\n');",
            f"    fs.writeFileSync('{render_file}', 'rendered');",
            f"    process.stdout.write('{remotion.DONE_PREFIX}' + JSON.stringify({{frames: 90, browsersOpened: 1}}) + '\\n');",
            "    process.exit(0);",
        ]
    lines += ["  }", "});"]
    return "\n".join(lines)


def _session(tmp_path, monkeypatch, script, **kwargs):
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    options = {
        "web_dir": tmp_path,
        "bundle_dir": tmp_path / "bundle",
        "props": tmp_path / "storyboard.json",
        "composition_id": "TestComposition",
        "on_metadata": lambda meta: {"out": str(tmp_path / "video.mp4"), "progressTotal": 90},
        "timeout_s": 30,
        "metadata_timeout_s": 10,
    }
    options.update(kwargs)
    return spawned, remotion.render_session(**options)


@requires_node
def test_session_carries_the_render_params_and_reports_one_browser(tmp_path, monkeypatch):
    script = _handshake_script(tmp_path)
    spawned, session = _session(tmp_path, monkeypatch, script)
    assert session["browsersOpened"] == 1
    assert session["frames"] == 90
    assert session["readySeconds"] >= 0
    params = json.loads((tmp_path / "confirm.json").read_text(encoding="utf-8"))
    assert params["out"].endswith("video.mp4")
    assert params["progressTotal"] == 90
    assert (tmp_path / "render.txt").is_file()
    assert spawned[0].poll() is not None


@requires_node
@pytest.mark.parametrize(
    "metadata",
    [
        {**METADATA, "durationInFrames": 91},
        {**METADATA, "width": 1078},
        {**METADATA, "fps": 25},
    ],
    ids=["frames", "width", "fps"],
)
def test_metadata_mismatch_aborts_before_any_frame_is_rendered(tmp_path, monkeypatch, metadata):
    """帧数/尺寸/帧率对不上时不得渲染：判定发生在确认之前。"""
    script = _handshake_script(tmp_path, metadata=metadata)
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))

    def confirm(meta):
        raise remotion.RemotionError(f"元数据不一致：{meta.duration_in_frames}")

    with pytest.raises(remotion.RemotionError, match="元数据不一致"):
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=confirm,
            timeout_s=30,
            metadata_timeout_s=10,
        )
    assert not (tmp_path / "render.txt").exists(), "校验失败时不得渲染任何一帧"
    assert (tmp_path / "abort.json").is_file(), "必须明确告诉 Node 不要渲染"
    assert spawned[0].poll() is not None, "会话必须被收掉"


@requires_node
def test_rejected_metadata_makes_the_script_exit_instead_of_waiting(tmp_path, monkeypatch):
    """Python 拒绝确认后，Node 自己退出（走 finally 关浏览器），不需要强杀。"""
    script = _handshake_script(tmp_path)
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    with pytest.raises(remotion.RemotionError, match="已取消渲染"):
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=lambda meta: None,
            timeout_s=30,
            metadata_timeout_s=10,
        )
    assert (tmp_path / "abort.json").is_file()
    assert spawned and spawned[0].poll() == 3, "脚本应以自己的退出码退出，而不是被强杀"


@requires_node
def test_silent_session_times_out_and_is_cleaned_up(tmp_path, monkeypatch):
    """报了元数据却永远不进入等待确认状态：必须超时，而不是永久阻塞。"""
    script = _handshake_script(tmp_path, ready=False, hang_after_metadata=True)
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    with pytest.raises(remotion.RemotionError, match="等待 composition 元数据超时"):
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=lambda meta: {"out": "x"},
            timeout_s=30,
            metadata_timeout_s=0.5,
        )
    assert spawned[0].poll() is not None, "超时后必须收掉进程树"


@requires_node
def test_session_that_exits_before_the_metadata_is_reported_with_the_exit_code(tmp_path, monkeypatch):
    script = "process.stderr.write('composition 选择失败\\n'); process.exit(7);"
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=lambda meta: {"out": "x"},
            timeout_s=30,
            metadata_timeout_s=10,
        )
    assert "退出码 7" in str(excinfo.value)
    assert "composition 选择失败" in str(excinfo.value)


@requires_node
def test_render_failure_reports_the_output_tail(tmp_path, monkeypatch):
    script = _handshake_script(tmp_path, confirm_exit=9, confirm_output="Target closed")
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=lambda meta: {"out": str(tmp_path / "video.mp4")},
            timeout_s=30,
            metadata_timeout_s=10,
        )
    message = str(excinfo.value)
    assert "退出码 9" in message and "Target closed" in message
    assert spawned[0].poll() is not None


@requires_node
def test_composition_id_mismatch_is_reported_before_rendering(tmp_path, monkeypatch):
    script = _handshake_script(tmp_path, metadata={**METADATA, "id": "Other"})
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script))
    with pytest.raises(remotion.RemotionError, match="期望"):
        remotion.render_session(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "storyboard.json",
            composition_id="TestComposition",
            on_metadata=lambda meta: {"out": "x"},
            timeout_s=30,
            metadata_timeout_s=10,
        )
    assert not (tmp_path / "render.txt").exists()


@requires_node
def test_a_session_that_lingers_after_done_is_not_reported_as_a_timeout(tmp_path, monkeypatch):
    """收到「渲染完成」之后 Node 迟迟不退出，不能被记成一次渲染超时。

    成片已经写出来了，剩下的只是进程收尾：超时后只收进程树，调用方照常拿到结果。
    """
    script = _handshake_script(tmp_path).replace(
        "    process.exit(0);",
        "    setInterval(() => {}, 1000);",  # 保持存活，模拟退出被拖住
    )
    monkeypatch.setattr(remotion, "_EXIT_GRACE_S", 0.5)
    spawned: list = []
    monkeypatch.setattr(remotion, "_spawn", _spawn_with(script, record=spawned))
    session = remotion.render_session(
        web_dir=tmp_path,
        bundle_dir=tmp_path / "bundle",
        props=tmp_path / "storyboard.json",
        composition_id="TestComposition",
        on_metadata=lambda meta: {"out": str(tmp_path / "video.mp4"), "progressTotal": 90},
        timeout_s=30,
        metadata_timeout_s=10,
    )
    assert session["frames"] == 90
    assert (tmp_path / "render.txt").is_file()
    assert spawned[0].poll() is not None, "拖延的会话必须被收掉"


# ---------------------------------------------------------------- 并发参数


def test_concurrency_must_be_a_positive_integer():
    assert remotion.check_concurrency(1) == 1
    assert remotion.check_concurrency(4) == 4
    for bad in (0, -1, True):
        with pytest.raises(remotion.RemotionError, match="正整数"):
            remotion.check_concurrency(bad)


@pytest.mark.parametrize("session_mode", [False, True])
def test_callback_error_terminates_process_before_closing_reader(tmp_path, monkeypatch, session_mode):
    """关闭管道前释放读锁：回调异常不能在清理时等待静默子进程。"""
    events = []

    class Process:
        stdout = None
        stdin = None

        def poll(self):
            return None

    class Reader:
        def __init__(self, stream):
            pass

        def read(self, timeout):
            return "progress"

        def close(self):
            events.append("close")

    def fail(line):
        raise RuntimeError("callback failed")

    monkeypatch.setattr(remotion, "_spawn", lambda *args, **kwargs: Process())
    monkeypatch.setattr(remotion, "_LineReader", Reader)
    monkeypatch.setattr(remotion, "_terminate_tree", lambda process: events.append("terminate"))
    with pytest.raises(RuntimeError, match="callback failed"):
        if session_mode:
            remotion.render_session(
                web_dir=tmp_path, bundle_dir=tmp_path, props=tmp_path / "props.json",
                composition_id="TestComposition",
                on_metadata=lambda meta: {}, timeout_s=1, on_line=fail,
            )
        else:
            remotion._run([], cwd=tmp_path, timeout_s=1, what="test", on_line=fail)
    assert events == ["terminate", "close"]


def test_render_frames_passes_the_concurrency_to_the_node_script(tmp_path, monkeypatch):
    captured: dict = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        Path(kwargs["cwd"]).joinpath("video.mp4").write_bytes(b"x")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(remotion, "_run", fake_run)
    out = tmp_path / "video.mp4"
    remotion.render_frames(
        web_dir=tmp_path,
        bundle_dir=tmp_path / "bundle",
        props=tmp_path / "props.json",
        composition_id="TestComposition",
        out=out,
        total_frames=5,
        crf=18,
        preset="medium",
        timeout_s=10,
        concurrency=3,
    )
    command = captured["command"]
    assert command[command.index("--concurrency") + 1] == "3"


def test_render_frames_rejects_an_invalid_concurrency_before_spawning(tmp_path, monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - 不该被调用
        raise AssertionError("非法并发必须在起进程之前失败")

    monkeypatch.setattr(remotion, "_run", explode)
    with pytest.raises(remotion.RemotionError, match="正整数"):
        remotion.render_frames(
            web_dir=tmp_path,
            bundle_dir=tmp_path / "bundle",
            props=tmp_path / "props.json",
            composition_id="TestComposition",
            out=tmp_path / "video.mp4",
            total_frames=5,
            crf=18,
            preset="medium",
            timeout_s=10,
            concurrency=0,
        )
