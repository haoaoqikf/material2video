"""访问权限回归测试。

成因见 a2v/security.py：Windows 的 ``tempfile.TemporaryDirectory()`` 会创建一个
**刻意收紧**的目录（只有 SYSTEM / Administrators / OWNER RIGHTS，且关闭继承）。
临时目录建在项目目录里时，中转出来的文件就把这份 ACL 带到最终位置，
既没有 Authenticated Users 也没有当前用户，于是以标准权限运行的打包应用
（Windows 11 新版媒体播放器）打不开成片，报 0x80070005。

注意：这个缺陷在 ``%TEMP%`` 下不会复现——那里的临时目录继承了一条宽松的
CREATOR OWNER ACE，会把问题掩盖掉。所以用例必须把临时目录建在目标目录里。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from a2v import prepare as prep, security
from a2v.encoder import VideoEncoder
from a2v.render import _grant_access
from conftest import make_jpeg, write_tone

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="权限问题只出现在 Windows")


def acl_entries(path: Path) -> list[str]:
    """返回 icacls 列出的授权行，用来判断权限是否正常。"""
    completed = subprocess.run(
        ["icacls", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    assert completed.returncode == 0, completed.stderr
    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if ":" in line and "Successfully processed" not in line
    ]


def assert_follows_parent_acl(path: Path) -> None:
    """断言文件不再自带 ACL，而是完全遵循目标目录的继承规则。

    这就是修复的实质：``icacls /reset`` 去掉临时目录带来的那套显式授权，
    换成从父目录继承。在真实项目目录里，父目录授权给 Authenticated Users，
    文件因此能被标准权限的播放器打开。
    """
    assert not security.needs_access_repair(path) or all(
        "(I)" in line for line in acl_entries(path)
    ), f"文件仍带有独立于父目录的授权：{acl_entries(path)}"


RESTRICT_PARENT = r"""
$path = {path}
$acl = Get-Acl -LiteralPath $path
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object {{ $acl.RemoveAccessRule($_) | Out-Null }}
foreach ($who in 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators') {{
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $who, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}}
Set-Acl -LiteralPath $path -AclObject $acl
"""


def make_restricted_parent(path: Path) -> Path:
    """造一个与项目目录等效的父目录：只有 SYSTEM / Administrators，关闭继承。

    ``%TEMP%`` 下的目录继承了一条宽松的 CREATOR OWNER ACE，会把缺陷掩盖掉；
    真实项目目录没有这条，所以用例必须自己造出这个环境。
    """
    path.mkdir(parents=True, exist_ok=True)
    script = RESTRICT_PARENT.format(path="'" + str(path).replace("'", "''") + "'")
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert completed.returncode == 0, completed.stderr
    return path


def stage_through_temp_dir(target: Path, content: bytes = b"staged") -> Path:
    """把文件经目标目录里的临时目录中转，复现「带出收紧 ACL」的现场。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        staged = Path(temp) / target.name
        staged.write_bytes(content)
        staged.replace(target)
    return target


def test_render_output_grants_access(tmp_path: Path) -> None:
    """成片经临时目录中转后，必须重新获得可访问的权限。"""
    jpeg = make_jpeg()
    video = tmp_path / "video.mp4"
    with VideoEncoder(video, fps=30) as encoder:
        for _ in range(3):
            encoder.write(jpeg)

    parent = make_restricted_parent(tmp_path / "unmasked")
    mirror = stage_through_temp_dir(parent / "mirror.mp4", video.read_bytes())
    assert security.needs_access_repair(mirror), "用例没有复现出问题现场"
    assert not all("(I)" in line for line in acl_entries(mirror))

    _grant_access(mirror)
    assert_follows_parent_acl(mirror)


def test_prepare_audio_cache_grants_access(tmp_path: Path, monkeypatch) -> None:
    """配音缓存文件同样经临时目录落地，也必须修复权限。"""
    text = "测试文本"

    async def fake(content, voice, rate, output):
        write_tone(output, 0.8)
        # 时间戳必须覆盖全部口播字符，否则字幕切分校验会失败
        return [
            {"text": char, "start": 0.1 + i * 0.15, "end": 0.2 + i * 0.15}
            for i, char in enumerate(text)
        ]

    monkeypatch.setattr(prep, "synthesize", fake)
    root = make_restricted_parent(tmp_path / "video")
    # 缓存目录也按项目目录的权限收紧，临时目录才会带出有问题的 ACL
    cache = make_restricted_parent(root / "cache")
    wav, _, _, hit = prep._scene_audio(text, "zh-CN-XiaoxiaoNeural", "+0%", cache, False)

    assert hit is False
    assert security.needs_access_repair(wav), "用例没有复现出问题现场"
    for produced in (wav, cache / f"{wav.stem}.json"):
        assert_follows_parent_acl(produced)
