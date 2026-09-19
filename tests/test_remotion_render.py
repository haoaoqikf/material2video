"""Remotion 渲染路径：Node 边界、构建输入指纹与端到端成片。

分三层：

- **边界**（不需要 Node）：依赖缺失时的报错、元数据行解析、失败时不留残件；
- **指纹**（需要仓库里的 `web/`）：构建输入覆盖面、别名键、以及「改了源码就判落后」；
- **端到端**（需要 `web/node_modules`，没有就跳过）：真渲几帧并逐项复核成片参数。

端到端部分跳过时**必须写清原因**：这套机检一直在消灭的失败模式就是
「看起来通过」与「其实没跑」长得一模一样。
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "examples" / "declarative-number" / "storyboard.json"

from a2v import remotion, render  # noqa: E402

WEB = ROOT / "web"


def _node_ready() -> bool:
    return (
        (WEB / "node_modules").is_dir()
        and shutil.which("node") is not None
        and shutil.which("npx") is not None
    )


requires_node = pytest.mark.skipif(
    not _node_ready(),
    reason="未安装前端依赖（cd web && pnpm install），Remotion 路径无法执行",
)


# ---------------------------------------------------------------- 边界


def test_missing_node_modules_reports_the_install_command(tmp_path):
    """依赖缺失必须报出**要跑哪条命令**：否则现场只看到一句「渲染失败」。"""
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion.require_environment(tmp_path)
    message = str(excinfo.value)
    assert "pnpm install" in message
    assert "node_modules" in message


def test_missing_web_project_says_where_it_looked(tmp_path):
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion.require_environment(tmp_path)
    assert "package.json" in str(excinfo.value)


def test_programs_are_resolved_to_full_paths():
    """`npx` 在 Windows 上是 `npx.cmd`，直接用它起进程会报「找不到文件」。"""
    resolved = pathlib.Path(remotion.program("node"))
    assert resolved.is_absolute()
    assert resolved.is_file()


def test_unknown_program_is_reported_with_the_node_requirement():
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion.program("a2v-no-such-program")
    assert "Node" in str(excinfo.value)


def test_metadata_line_is_parsed_and_the_last_one_wins():
    lines = [
        "Bundling 50%",
        f'{remotion.METADATA_PREFIX}{{"id": "A2V", "fps": 25, "width": 1, "height": 1, "durationInFrames": 1}}',
        "noise",
        f'{remotion.METADATA_PREFIX}{{"id": "A2V", "fps": 30, "width": 1080, "height": 1920, "durationInFrames": 180}}',
    ]
    payload = remotion._metadata_from(lines)
    assert payload is not None
    assert payload["durationInFrames"] == 180


def test_metadata_line_that_is_not_json_is_reported():
    with pytest.raises(remotion.RemotionError) as excinfo:
        remotion._metadata_from([f"{remotion.METADATA_PREFIX}not json"])
    assert "JSON" in str(excinfo.value)


def test_absent_metadata_line_is_reported_as_such():
    assert remotion._metadata_from(["nothing here"]) is None


def test_composition_metadata_contract_shape():
    meta = remotion.CompositionMetadata(fps=30, width=1080, height=1920, duration_in_frames=180)
    contract = meta.contract
    assert (contract.fps, contract.width, contract.height) == (30, 1080, 1920)
    assert contract.duration_in_frames == 180
    # 与网页契约同一形状，因此三条判定函数可以直接复用
    assert render._resolve_total_frames(contract, None) == 180


# ---------------------------------------------------------------- 构建输入指纹


def test_build_input_fingerprint_covers_source_styles_fonts_and_lockfile():
    """分量与编码都由这些文件决定，少一项就会出现「源码改了但判为当前」。"""
    files = remotion.build_input_fingerprint()["files"]
    assert "__a2v_web__/src/compositions/A2VComposition.tsx" in files
    assert "__a2v_web__/src/styles/tokens.css" in files
    assert "__a2v_web__/src/assets/fonts.json" in files
    assert "__a2v_web__/package.json" in files
    assert "__a2v_web__/pnpm-lock.yaml" in files
    assert "__a2v_web__/scripts/remotion-render.mjs" in files
    # 字体记的是源文件（别名键），不是构建出来的副本
    assert any(key.startswith("__a2v__/fonts/") for key in files)


def test_fingerprint_keys_survive_a_workspace_root_outside_the_repo():
    """内容根外置时构建输入全在工作区根之外，键仍必须是可复核的别名键。"""
    files = remotion.build_input_fingerprint()["files"]
    assert all(key.count("/") >= 1 for key in files), "出现了只剩文件名的键"


def test_tests_and_build_artifacts_are_not_build_inputs():
    keys = set(remotion.build_input_fingerprint()["files"])
    assert not any(".test." in key for key in keys)
    assert not any("/node_modules/" in key for key in keys)
    assert not any("/dist/" in key for key in keys)
    # 契约页只用于体检，不参与成片：改它不该让成片判成落后
    assert not any("/contract/" in key for key in keys)
    assert not any("vite.config" in key for key in keys)


def test_an_unreferenced_file_change_does_not_mark_videos_stale(tmp_path):
    """改一个画面用不到的文件不该报「落后」。

    这条与「改了组件要报落后」同等重要：闸门一旦被噪音淹没，人就开始忽略它，
    而一个被忽略的闸门等于没有闸门。
    """
    unused = WEB / "src" / "contract" / "main.tsx"
    original = unused.read_bytes()
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    (tmp_path / "video.provenance.json").write_text(
        json.dumps(
            {
                "version": 4,
                "renderer": "remotion",
                "workspace": str(ROOT),
                "page": "web/src/index.ts",
                "assets": remotion.build_input_fingerprint(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert render.provenance_status(video)["status"] == "current"
    try:
        unused.write_bytes(original + "\n// 与画面无关的改动\n".encode())
        assert render.provenance_status(video)["status"] == "current"
    finally:
        unused.write_bytes(original)


def test_fingerprint_is_stable_between_calls():
    assert remotion.build_input_fingerprint() == remotion.build_input_fingerprint()


# ---------------------------------------------------------------- 溯源


def test_provenance_status_turns_stale_when_a_component_changes(tmp_path):
    """这份溯源的全部意义就是这一条：改了组件源码，旧成片必须被判「落后」。"""
    component = WEB / "src" / "compositions" / "A2VComposition.tsx"
    original = component.read_bytes()
    video = tmp_path / "video.mp4"
    video.write_bytes(b"not really a video")
    (tmp_path / "video.provenance.json").write_text(
        json.dumps(
            {
                "version": 4,
                "renderer": "remotion",
                "workspace": str(ROOT),
                "page": "web/src/index.ts",
                "assets": remotion.build_input_fingerprint(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert render.provenance_status(video)["status"] == "current"

    try:
        component.write_bytes(original + "\n// 改一行\n".encode())
        status = render.provenance_status(video)
        assert status["status"] == "stale"
        assert any("A2VComposition" in key for key in status["changed"])
    finally:
        component.write_bytes(original)
    assert render.provenance_status(video)["status"] == "current"


def test_provenance_of_an_unknown_renderer_version_is_not_trusted(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    (tmp_path / "video.provenance.json").write_text(
        json.dumps({"version": 2, "assets": {"files": {}}}), encoding="utf-8"
    )
    status = render.provenance_status(video)
    assert status["status"] == "unknown"
    assert "version=2" in status["detail"]


# ---------------------------------------------------------------- 端到端


@requires_node
def test_renders_a_short_clip_with_the_expected_stream_parameters(tmp_path):
    """真渲一小段，并复核帧数、分辨率、帧率与像素格式。

    这几项不是风格选项：`yuv420p(tv, bt709)` 决定播放器能不能正确解出颜色，
    帧数决定成片长度与字幕是否对得上。
    """
    output = tmp_path / "clip.mp4"
    result = render.render_with_remotion(
        output=output,
        storyboard=_model(),
        storyboard_path=STORYBOARD,
        limit_frames=3,
        probe=True,
        workspace_root=ROOT,
    )
    assert output.is_file() and output.stat().st_size > 0
    assert (result.frames, result.fps, result.width, result.height) == (3, 30, 1080, 1920)
    # 码流参数与网页路径同一套验收口径：像素格式不对时 Windows 播放器会拒绝打开
    info = _stream_info(output)
    assert "1080x1920" in info
    assert "yuv420p(tv, bt709" in info
    assert "yuvj420p" not in info
    # 溯源必须写出来并指向构建输入
    provenance = json.loads(output.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    assert provenance["renderer"] == "remotion"
    assert provenance["frames"] == 3
    assert len(provenance["assets"]["files"]) > 10


def _stream_info(path: pathlib.Path) -> str:
    from imageio_ffmpeg import get_ffmpeg_exe

    completed = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stderr


@requires_node
def test_frame_count_mismatch_stops_before_rendering(tmp_path):
    """画面声明的总帧数与分镜累计不一致时必须**渲染前**终止。

    让它渲完再看长度，等于把「两份数据不一致」变成一支看起来正常的片子。
    """
    model = _model()
    squeezed = pathlib.Path(tmp_path / "storyboard.json")
    payload = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    payload["scenes"][0]["durationInFrames"] -= 10
    squeezed.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = tmp_path / "clip.mp4"
    with pytest.raises(render.RenderError) as excinfo:
        render.render_with_remotion(
            output=output,
            storyboard=model,
            storyboard_path=squeezed,
            probe=False,
            workspace_root=ROOT,
        )
    message = str(excinfo.value)
    assert "180" in message and "170" in message
    assert not output.exists(), "校验失败时不应留下成片"


def _model():
    from a2v import storyboard as sb

    model, report = sb.load(STORYBOARD, declarative=True)
    assert model is not None and report.ok, report.issues
    return model
