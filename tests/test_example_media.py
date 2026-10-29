"""示例固定媒体恢复：配方与登记一致、缓存跳过、失败不覆盖已有素材。"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.example_media import restore
from example_catalog import EXAMPLE_PATHS

ROOT = Path(__file__).resolve().parents[1]
FIXED_EXAMPLES = ("american-science-milestones", "solar-system-journey")
TRANSFORMS = {"copy", "jpeg-q3", "tiff-png", "specular-roughness", "moon-continuous-silent", "generate"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_media(path: Path, *, kind: str = "image", size: str = "64x48", color: str = "0x334455") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "image":
        command = [get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s={size}",
                   "-frames:v", "1", str(path)]
    else:
        command = [get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                   "-i", f"color=c={color}:s={size}:r=30:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(command, check=True)
    return path


def write_example(root: Path, entries: list[dict], recipes: list[dict]) -> None:
    assets = root / "assets"
    (assets / "media").mkdir(parents=True, exist_ok=True)
    (assets / "media-sources.json").write_text(
        json.dumps({"schemaVersion": 1, "assets": entries}, ensure_ascii=False), encoding="utf-8")
    (assets / "recipe.json").write_text(
        json.dumps({"schemaVersion": 1, "assets": recipes}, ensure_ascii=False), encoding="utf-8")


def registered(tmp_path: Path, kind: str = "image", *, size: str = "64x48", color: str = "0x334455",
               identity: str = "photo") -> tuple[Path, bytes, dict, dict]:
    """按内容摘要生成一份媒体和对应登记项；返回 (根目录, 字节, 登记, 配方)。"""
    source = make_media(tmp_path / f"{identity}-source.{'mp4' if kind == 'video' else 'png'}",
                        kind=kind, size=size, color=color)
    data = source.read_bytes()
    width, height = (int(value) for value in size.split("x"))
    digest = sha256(data)
    relative = f"assets/media/{digest}.{'mp4' if kind == 'video' else 'png'}"
    root = tmp_path / "example"
    entry = {"id": identity, "path": relative, "kind": kind, "width": width, "height": height,
             "durationSeconds": 1.0 if kind == "video" else None, "sha256": digest}
    recipe = {"id": identity, "transform": "copy", "downloadUrl": f"https://example.invalid/{identity}",
              "expectedSha256": digest}
    write_example(root, [entry], [recipe])
    return root, data, entry, recipe


def test_fixed_example_recipes_match_registered_assets() -> None:
    """示例配方必须完整覆盖登记且摘要一致，避免恢复出与登记不同的文件。"""
    for name in FIXED_EXAMPLES:
        root = EXAMPLE_PATHS[name]
        sources = json.loads((root / "assets/media-sources.json").read_text(encoding="utf-8"))
        recipe = json.loads((root / "assets/recipe.json").read_text(encoding="utf-8"))
        registered_assets = {item["id"]: item for item in sources["assets"]}
        recipes = {item["id"]: item for item in recipe["assets"]}
        assert registered_assets.keys() == recipes.keys()
        for identity, item in recipes.items():
            assert item["transform"] in TRANSFORMS, f"{name}/{identity} 有未知转换"
            assert item["expectedSha256"] == registered_assets[identity]["sha256"]
            if item["transform"] == "generate":
                assert item["downloadUrl"] is None
            else:
                assert item["downloadUrl"].startswith("https://")


def test_restore_downloads_into_empty_example(tmp_path: Path) -> None:
    root, data, entry, _recipe = registered(tmp_path)
    calls = []

    def fetch(url: str, target: Path) -> None:
        calls.append(url)
        target.write_bytes(data)

    restore(root, fetch=fetch)
    assert (root / entry["path"]).read_bytes() == data
    assert calls == ["https://example.invalid/photo"]


def test_correct_cache_is_skipped_without_network(tmp_path: Path) -> None:
    root, data, entry, _recipe = registered(tmp_path)
    target = root / entry["path"]
    target.write_bytes(data)

    def fetch(url: str, target: Path) -> None:
        raise AssertionError("缓存命中时不应下载")

    restore(root, fetch=fetch)
    assert target.read_bytes() == data


def test_shared_content_path_is_restored_once(tmp_path: Path) -> None:
    """多个 ID 可指向同一内容寻址文件，恢复时只下载一次。"""
    root, data, entry, recipe = registered(tmp_path)
    write_example(root, [entry, {**entry, "id": "alias"}],
                  [recipe, {**recipe, "id": "alias"}])
    calls = []

    def fetch(url: str, target: Path) -> None:
        calls.append(url)
        target.write_bytes(data)

    restore(root, fetch=fetch)
    assert len(calls) == 1
    assert (root / entry["path"]).read_bytes() == data


def test_failed_download_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    root, _data, entry, _recipe = registered(tmp_path)
    target = root / entry["path"]
    target.write_bytes(b"broken")

    def fetch(url: str, target: Path) -> None:
        raise RuntimeError("模拟下载失败")

    with pytest.raises(RuntimeError, match="模拟下载失败"):
        restore(root, fetch=fetch)
    assert target.read_bytes() == b"broken"
    assert list(target.parent.glob("*.partial")) == []


def test_failure_does_not_install_other_staged_media(tmp_path: Path) -> None:
    """一批恢复要么全部安装，要么都不落盘，避免留下半套素材。"""
    root, first, first_entry, first_recipe = registered(tmp_path, identity="first")
    second_source = make_media(tmp_path / "second-source.png", color="0x112233")
    second_data = second_source.read_bytes()
    second_digest = sha256(second_data)
    second_entry = {"id": "second", "path": f"assets/media/{second_digest}.png", "kind": "image",
                    "width": 64, "height": 48, "durationSeconds": None, "sha256": second_digest}
    second_recipe = {"id": "second", "transform": "copy", "downloadUrl": "https://example.invalid/second",
                     "expectedSha256": second_digest}
    write_example(root, [first_entry, second_entry], [first_recipe, second_recipe])

    def fetch(url: str, target: Path) -> None:
        if url.endswith("second"):
            raise RuntimeError("模拟第二项失败")
        target.write_bytes(first)

    with pytest.raises(RuntimeError, match="模拟第二项失败"):
        restore(root, fetch=fetch)
    assert not (root / first_entry["path"]).exists()
    assert not (root / second_entry["path"]).exists()


def test_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    root, _data, entry, _recipe = registered(tmp_path)

    def fetch(url: str, target: Path) -> None:
        target.write_bytes(b"not the registered bytes")

    with pytest.raises(RuntimeError, match="SHA-256"):
        restore(root, fetch=fetch)
    assert not (root / entry["path"]).exists()


def test_wrong_dimensions_are_rejected(tmp_path: Path) -> None:
    root, data, entry, _recipe = registered(tmp_path)
    entry["width"], entry["height"] = 32, 24
    write_example(root, [entry], [_recipe])

    def fetch(url: str, target: Path) -> None:
        target.write_bytes(data)

    with pytest.raises(RuntimeError, match="尺寸"):
        restore(root, fetch=fetch)


def test_video_duration_is_checked(tmp_path: Path) -> None:
    root, data, entry, recipe = registered(tmp_path, kind="video")
    target = root / entry["path"]
    target.write_bytes(data)
    restore(root, fetch=lambda _url, _target: None)
    entry["durationSeconds"] = 2.0
    write_example(root, [entry], [recipe])
    with pytest.raises(RuntimeError, match="时长"):
        restore(root, fetch=lambda _url, _target: None)


def test_generate_requires_generator_and_does_not_leave_output(tmp_path: Path) -> None:
    root, data, entry, recipe = registered(tmp_path)
    recipe.update(transform="generate", downloadUrl=None)
    write_example(root, [entry], [recipe])
    with pytest.raises(ValueError, match="缺少生成器"):
        restore(root)

    def generate(item: dict, target: Path) -> None:
        raise RuntimeError("模拟生成失败")

    with pytest.raises(RuntimeError, match="模拟生成失败"):
        restore(root, generate=generate)
    assert not (root / entry["path"]).exists()


def test_generator_output_is_validated_and_installed(tmp_path: Path) -> None:
    root, data, entry, recipe = registered(tmp_path)
    recipe.update(transform="generate", downloadUrl=None)
    write_example(root, [entry], [recipe])
    restore(root, generate=lambda _item, target: target.write_bytes(data))
    assert (root / entry["path"]).read_bytes() == data


def test_media_path_outside_media_directory_is_rejected(tmp_path: Path) -> None:
    root, _data, entry, recipe = registered(tmp_path)
    entry["path"] = "assets/outside.png"
    write_example(root, [entry], [recipe])
    with pytest.raises(ValueError, match="越界"):
        restore(root)


def test_recipe_must_cover_registered_assets(tmp_path: Path) -> None:
    root, _data, entry, recipe = registered(tmp_path)
    write_example(root, [entry], [])
    with pytest.raises(ValueError, match="对应"):
        restore(root)
    recipe["expectedSha256"] = "0" * 64
    write_example(root, [entry], [recipe])
    with pytest.raises(ValueError, match="摘要不一致"):
        restore(root)
