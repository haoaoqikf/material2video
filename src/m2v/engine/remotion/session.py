"""渲染会话：取元数据、校验通过后再渲染，以及静帧与逐帧两条旧路径。

会话是 Python 与 Node 之间唯一的**双向**通道：Node 只开一个浏览器，选出
composition 之后把真实元数据报回来，然后停在原地等确认。`render_session`
就是这条协议的状态机——起进程、等元数据、下发确认、收进度、收尾并归类错误——
因此它被拆成若干小函数，每段只负责一个阶段，而协议本身逐字不变。
"""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import m2v.engine.perf as perf

from .process import (
    ABORT_PREFIX,
    CONFIRM_PREFIX,
    DEFAULT_CONCURRENCY,
    DONE_PREFIX,
    METADATA_PREFIX,
    PROGRESS_PREFIX,
    READY_PREFIX,
    RENDER_SCRIPT,
    SESSION_PREFIX,
    RemotionError,
    _ABORT_GRACE_S,
    _EOF,
    _EXIT_GRACE_S,
    _LineReader,
    _METADATA_TIMEOUT_S,
    _run,
    _spawn,
    _tail_text,
    _terminate_tree,
    check_concurrency,
    program,
)

#: 日志名保持拆包前的 `m2v.engine.remotion`：订阅方与输出格式都不需要改。
logger = logging.getLogger(__package__)


@dataclass(frozen=True)
class CompositionMetadata:
    """composition 从分镜 props 推导出来的画面参数。"""

    fps: int
    width: int
    height: int
    duration_in_frames: int


def progress_handler(total_frames: int) -> Callable[[str], None]:
    """把 `__M2V_PROGRESS__` 行翻译成人看的进度日志，每 10% 报一次。"""

    state = {"last": -10}

    def report(line: str) -> None:
        if not line.startswith(PROGRESS_PREFIX):
            return
        percent = _safe_int(line[len(PROGRESS_PREFIX) :])
        if percent is None or percent < state["last"] + 10:
            return
        state["last"] = percent
        logger.info(
            "渲染进度 %d%%（约 %d/%d 帧）", percent, total_frames * percent // 100, total_frames
        )

    return report


def _safe_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


def _metadata_from(lines: list[str]) -> dict | None:
    """从输出里取元数据行。

    取**最后**一条：打包器与 Remotion 自己的日志都可能出现在前面，
    而元数据是脚本在渲染前打印的，重放时最后一条才是本次的。
    """
    found: dict | None = None
    for line in lines:
        if not line.startswith(METADATA_PREFIX):
            continue
        try:
            found = json.loads(line[len(METADATA_PREFIX) :])
        except json.JSONDecodeError as exc:
            raise RemotionError(f"composition 元数据不是合法 JSON：{line!r}（{exc}）") from exc
    return found


def metadata(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str,
    timeout_s: float = _METADATA_TIMEOUT_S,
) -> CompositionMetadata:
    """读出 composition 由分镜 props 推导出的画面参数。"""
    lines: list[str] = []
    _run(
        [
            program("node"),
            RENDER_SCRIPT,
            "--bundle",
            str(bundle_dir),
            "--props",
            str(props),
            "--composition-id",
            composition_id,
            "--metadata-only",
        ],
        cwd=web_dir,
        timeout_s=timeout_s,
        what="读取 composition 元数据",
        on_line=lines.append,
    )
    payload = _metadata_from(lines)
    if payload is None:
        raise RemotionError(
            f"渲染脚本没有报出 composition 元数据（应有一行以 {METADATA_PREFIX} 开头）。"
            f"输出：\n" + "\n".join(lines[-10:])
        )
    if payload.get("id") != composition_id:
        raise RemotionError(
            f"渲染脚本选中的 composition 是 {payload.get('id')!r}，期望 {composition_id!r}"
        )
    return CompositionMetadata(
        fps=int(payload["fps"]),
        width=int(payload["width"]),
        height=int(payload["height"]),
        duration_in_frames=int(payload["durationInFrames"]),
    )


def render_still(*, web_dir: Path, bundle_dir: Path, props: Path, out: Path,
                 frame: int, scale: int, composition_id: str) -> None:
    """无损 PNG 静帧；不经 JPEG 或 MP4 中转，保留原生采集的像素细节。"""
    _run([program("node"), RENDER_SCRIPT, "--bundle", str(bundle_dir), "--props", str(props),
          "--composition-id", composition_id, "--out", str(out), "--still-frame", str(frame),
          "--scale", str(scale)], cwd=web_dir, timeout_s=1800, what="合成原生静帧")
    if not out.is_file() or out.stat().st_size == 0:
        raise RemotionError(f"静帧渲染完成后没有产出文件：{out}")


def render_frames(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    out: Path,
    total_frames: int,
    crf: int,
    preset: str,
    timeout_s: float,
    frame_start: int = 0,
    scale: float = 1,
    composition_id: str,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> None:
    """把 composition 渲染并编码成无声 MP4。

    音频不在这里合成：配音与字幕的合成、成片验收与交付权限都留在 Python 侧，
    与旧路径共用同一段代码，因此两条路径的成片参数不会各走一套。

    这条路径每次单独起 Node（元数据由调用方另行读取），保留给金融专题导出等
    需要分别控制两步的调用方；文章正式渲染走 :func:`render_session`。
    """
    concurrency = check_concurrency(concurrency)
    command = [
        program("node"),
        RENDER_SCRIPT,
        "--bundle",
        str(bundle_dir),
        "--props",
        str(props),
        "--composition-id",
        composition_id,
        "--out",
        str(out),
        "--crf",
        str(crf),
        "--preset",
        preset,
        # 显式给出帧区间：composition 自己也有时长，但**渲染的帧数**是验收项，
        # 让它由 Python 算出来并在命令行上写死，比隐含在画面里可核对
        "--frames",
        f"{frame_start}-{frame_start + total_frames - 1}",
        "--scale",
        str(scale),
        "--concurrency",
        str(concurrency),
    ]
    _run(
        command,
        cwd=web_dir,
        timeout_s=timeout_s,
        what=f"渲染 {total_frames} 帧",
        on_line=progress_handler(total_frames),
    )
    if not out.is_file() or out.stat().st_size == 0:
        raise RemotionError(f"渲染完成后没有产出文件：{out}")


# ---------------------------------------------------------------- 会话状态机


@dataclass
class _SessionState:
    """一次会话的可变状态：进程、读行器与已收到的回报。

    会话是一条**有状态的行协议**（先握手、再确认、后渲染），把状态收进一个对象，
    各阶段函数才不必互相传一长串参数，也才能单独看住自己那一段的行为。
    """

    process: subprocess.Popen[str]
    reader: _LineReader
    #: 已收到的输出行；只留尾部窗口，失败时用它报出原因
    tail: list[str]
    #: Node 回报的会话信息（浏览器开启次数、完成回报）与 `ready` 标记
    session: dict
    #: 可替换的进度回调：总帧数要等确认下发之后才知道
    sink: dict[str, Callable[[str], None] | None]
    memory_sampler: perf.ProcessTreeMemorySampler | None
    #: 起进程的时刻；报告里的「元数据」阶段从它算起
    handshake_started: float
    metadata: CompositionMetadata | None = None
    returncode: int | None = None
    done: bool = False


def _session_command(bundle_dir: Path, props: Path, composition_id: str) -> list[str]:
    """会话模式的命令行：不指定输出，等 Python 下发确认后再渲染。"""
    return [
        program("node"),
        RENDER_SCRIPT,
        "--bundle",
        str(bundle_dir),
        "--props",
        str(props),
        "--composition-id",
        composition_id,
        "--session",
    ]


def _open_session(
    command: list[str], web_dir: Path, on_line: Callable[[str], None] | None
) -> _SessionState:
    """起会话子进程，接上读行器并开始采样它的内存。"""
    process = _spawn(command, web_dir, stdin=subprocess.PIPE)
    memory_sampler = perf.ProcessTreeMemorySampler(process.pid) if getattr(process, "pid", None) else None
    if memory_sampler is not None:
        memory_sampler.start()
    return _SessionState(
        process=process,
        reader=_LineReader(process.stdout),
        tail=[],
        session={},
        sink={"handler": on_line},
        memory_sampler=memory_sampler,
        handshake_started=time.monotonic(),
    )


def _consume(state: _SessionState, line: str) -> None:
    """收下一行输出：进尾部窗口，并交给当前生效的进度回调。"""
    state.tail.append(line)
    if len(state.tail) > 200:
        del state.tail[0]
    handler = state.sink["handler"]
    if handler is not None:
        handler(line)


def _abort(state: _SessionState, reason: str) -> None:
    """把「不渲染」明确告诉 Node，再收掉进程树。

    先给 Node 一小段时间**优雅退出**：它会走 `finally` 关掉浏览器再退出，
    比直接杀进程树干净（否则 Chromium 会被强杀，留下孤儿进程占着内存）。
    超时仍未退出才强杀整棵树。
    """
    stdin = state.process.stdin
    if stdin is not None and not stdin.closed:
        try:
            stdin.write(f"{ABORT_PREFIX}{json.dumps({'reason': reason}, ensure_ascii=False)}\n")
            stdin.flush()
        except (OSError, ValueError):  # pragma: no cover - 进程已经退出
            pass
        with contextlib.suppress(OSError, ValueError):
            stdin.close()
    with contextlib.suppress(subprocess.TimeoutExpired):
        state.process.wait(timeout=_ABORT_GRACE_S)
    _terminate_tree(state.process)


def _await_metadata(
    state: _SessionState, composition_id: str, timeout_s: float
) -> CompositionMetadata:
    """等 Node 报出 composition 元数据，并进入等待确认状态。

    超时与提前退出都在这里定性：前者说明脚本既没报元数据也没等确认，后者带上
    退出码与输出尾部——两者都不该退化成一次「渲染失败」。
    """
    deadline = time.monotonic() + timeout_s
    while state.metadata is None or not state.session.get("ready"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _abort(state, "等待 composition 元数据超时")
            raise RemotionError(
                f"等待 composition 元数据超时（超过 {timeout_s:.0f} 秒）："
                f"渲染脚本没有报出元数据或没有进入等待确认状态。\n{_tail_text(state.tail)}"
            )
        line = state.reader.read(min(remaining, 1.0))
        if line is None:
            continue
        if line is _EOF:
            state.returncode = state.process.wait()
            raise RemotionError(
                f"渲染脚本在开始渲染前就退出了（退出码 {state.returncode}）：\n{_tail_text(state.tail)}"
            )
        _consume(state, line)
        if line.startswith(METADATA_PREFIX):
            payload = _metadata_from([line])
            if payload is None:  # pragma: no cover - 前缀已匹配
                continue
            state.metadata = CompositionMetadata(
                fps=int(payload["fps"]),
                width=int(payload["width"]),
                height=int(payload["height"]),
                duration_in_frames=int(payload["durationInFrames"]),
            )
            if payload.get("id") != composition_id:
                _abort(state, "composition 标识不匹配")
                raise RemotionError(
                    f"渲染脚本选中的 composition 是 {payload.get('id')!r}，期望 {composition_id!r}"
                )
        elif line.startswith(SESSION_PREFIX):
            state.session.update(json.loads(line[len(SESSION_PREFIX) :]))
        elif line.startswith(READY_PREFIX):
            state.session["ready"] = True
    if state.metadata is None:  # pragma: no cover - 循环条件已保证
        _abort(state, "没有元数据")
        raise RemotionError("渲染脚本没有报出 composition 元数据")
    return state.metadata


def _confirm(
    state: _SessionState,
    metadata: CompositionMetadata,
    on_metadata: Callable[[CompositionMetadata], dict | None],
) -> None:
    """把 Python 侧的判定结果下发给 Node；不通过就取消渲染。

    `on_metadata` 抛错或返回 `None` 都表示校验没过：向 Node 发 `ABORT` 并收掉
    整棵进程树，异常原样抛出。确认下发之后进度回调才接管——总帧数来自参数。
    """
    try:
        params = on_metadata(metadata)
    except BaseException:
        _abort(state, "Python 侧未通过元数据校验")
        raise
    if params is None:
        _abort(state, "Python 侧未通过元数据校验")
        raise RemotionError("元数据校验未通过，已取消渲染")
    assert state.process.stdin is not None
    state.process.stdin.write(f"{CONFIRM_PREFIX}{json.dumps(params, ensure_ascii=False)}\n")
    state.process.stdin.flush()
    # 握手结束：从起进程到确认下发，就是报告里的「元数据」阶段
    state.session["readySeconds"] = time.monotonic() - state.handshake_started
    if state.sink["handler"] is None:
        total = params.get("progressTotal")
        if isinstance(total, int) and total > 0:
            state.sink["handler"] = progress_handler(total)


def _collect_render(state: _SessionState, timeout_s: float) -> None:
    """收渲染阶段的输出，直到 Node 报出完成或退出。

    超时同样按截止时间判定：渲染中途长时间不输出也必须照样超时。
    """
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _abort(state, "渲染超时")
            raise RemotionError(f"渲染超时（超过 {timeout_s:.0f} 秒）")
        line = state.reader.read(min(remaining, 1.0))
        if line is None:
            continue
        if line is _EOF:
            break
        _consume(state, line)
        if line.startswith(DONE_PREFIX):
            state.session.update(json.loads(line[len(DONE_PREFIX) :]))
            state.done = True
            break


def _wait_for_exit(state: _SessionState) -> None:
    """等 Node 自己退出，并记下退出码。

    已经收到「渲染完成」时，Node 之后卡在退出上也**不能**算成一次超时：
    给它一段时间自己收尾，超时就只收进程树（成片随后照常验收）。
    """
    if not state.done:
        state.returncode = state.process.wait()
        return
    try:
        state.returncode = state.process.wait(timeout=_EXIT_GRACE_S)
    except subprocess.TimeoutExpired:
        logger.warning("渲染脚本在回报完成后仍未退出，收回进程树")
        _terminate_tree(state.process)
        state.returncode = state.process.wait()


def _cleanup(state: _SessionState) -> None:
    """无论怎么收场都收掉进程树、管道与内存采样。

    协议解析或进度回调也可能抛错，不能让 `close` 等待仍存活的静默进程：
    因此先终止进程释放读操作，再关管道。
    """
    if state.process.poll() is None:
        _terminate_tree(state.process)
    state.reader.close()
    if state.process.stdin is not None and not state.process.stdin.closed:
        with contextlib.suppress(OSError, ValueError):
            state.process.stdin.close()
    state.session["peakMemoryBytes"] = state.memory_sampler.stop() if state.memory_sampler is not None else None
    state.session["memorySamples"] = state.memory_sampler.samples if state.memory_sampler is not None else 0


def _raise_if_failed(state: _SessionState, metadata: CompositionMetadata) -> None:
    """把收场结果翻译成错误：退出码与异常帧数。

    `done` 时退出码可能是收进程树留下的，不代表渲染失败；成片随后照常验收。
    """
    if state.returncode != 0 and not state.done:
        raise RemotionError(f"渲染 {metadata.duration_in_frames} 帧失败（退出码 {state.returncode}）：\n{_tail_text(state.tail)}")
    expected = state.session.get("frames")
    if isinstance(expected, int) and expected < 1:
        raise RemotionError(f"渲染脚本回报了异常的帧数：{expected}")


def render_session(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str,
    on_metadata: Callable[[CompositionMetadata], dict | None],
    timeout_s: float,
    metadata_timeout_s: float = _METADATA_TIMEOUT_S,
    on_line: Callable[[str], None] | None = None,
) -> dict:
    """在**同一个 Node 会话**里先取元数据、校验通过后再渲染。

    两次进程调用（一次取元数据、一次渲染）各自冷启动浏览器并各选一次
    composition。这里把两件事压进一个会话：Node 只开一个浏览器，选择
    composition 之后把真实元数据报回来，然后**停在原地等确认**。

    `on_metadata` 是判定入口：它拿到元数据后做交叉校验，返回要下发的渲染参数；
    校验不通过时它应当抛错——那时本函数向 Node 发 `ABORT` 并收掉整棵进程树，
    异常原样抛出。因此「帧数/尺寸/帧率不匹配」的代价是一次选择而不是一次渲染。

    返回会话信息（浏览器开启次数、完成回报），供性能报告留证。
    """
    state = _open_session(_session_command(bundle_dir, props, composition_id), web_dir, on_line)
    try:
        metadata = _await_metadata(state, composition_id, metadata_timeout_s)
        _confirm(state, metadata, on_metadata)
        _collect_render(state, timeout_s)
        _wait_for_exit(state)
    except KeyboardInterrupt:
        _abort(state, "用户中断")
        raise
    finally:
        _cleanup(state)
    _raise_if_failed(state, metadata)
    return state.session
