"""一次完整生成；持久候选支持验收与交付重试。"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from . import security
from .errors import M2VError
from .fingerprints import fingerprint
from .project import _write_json


def _save(path, value):
    # Windows 防病毒/索引器可能短暂占用刚替换的 JSON；只重试共享冲突。
    for attempt in range(6):
        try:
            _write_json(path, value)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.05 * (attempt + 1))

logger = logging.getLogger(__name__)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def outputs(root: Path) -> Path:
    # 示例与正式作品的产物都归属作品目录本身；示例源与产物仍由忽略规则分开。
    return root / "outputs"


def read_record(directory: Path) -> dict:
    try:
        value = json.loads((directory / "delivery.json").read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def candidate(root: Path, prepared: dict) -> dict:
    record = read_record(outputs(root))
    if record.get("preparedFingerprint") != prepared["preparedFingerprint"]:
        raise M2VError("缺少当前完整候选；请执行 m2v render")
    try:
        from m2v.standalone.executor import local_artifact
        path = local_artifact(root, record.get('path'))
        valid = path.is_file() and digest(path) == record.get("sha256")
    except (OSError, TypeError):
        valid = False
    if not valid:
        raise M2VError("候选文件缺失或摘要变化；请执行 m2v render")
    parameters = record.get('parameters')
    if not isinstance(parameters, dict):
        raise M2VError('候选渲染参数结构损坏；请重新render')
    expected = binding(root, prepared, parameters)
    if (any(record.get(k) != v for k, v in expected.items())
            or fingerprint(expected) != record.get('key')):
        raise M2VError("候选实现或渲染参数已变化；请执行 m2v render")
    # 持久凭据保持相对路径；仅当前调用的返回值解析为实际作品位置。
    return {**record, 'path': str(path)}


@contextmanager
def _lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "delivery.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise M2VError(f"作品正在生成或验收，拒绝重复执行；若进程已异常退出，请移除 {path}") from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _publish(source: Path, destination: Path, sha256: str) -> None:
    """旁车先发布、视频最后替换；任一步失败恢复旧旁车，旧视频始终有效。"""
    with tempfile.TemporaryDirectory(prefix="delivery-", dir=destination.parent) as temporary:
        work = Path(temporary)
        pending, backups = [], {}
        for suffix in (".provenance.json", ".performance.json"):
            original = source.with_suffix(suffix)
            target = destination.with_suffix(suffix)
            if original.is_file():
                copied = work / ("video" + suffix)
                shutil.copyfile(original, copied)
                if target.is_file():
                    backup = work / ("old" + suffix)
                    shutil.copyfile(target, backup)
                    backups[target] = backup
                else:
                    backups[target] = None
                pending.append((copied, target))
        video = None
        if not destination.is_file() or digest(destination) != sha256:
            video = work / "video.mp4"
            shutil.copyfile(source, video)
        published = []
        try:
            for copied, target in pending:
                security.deliver(copied, target)
                published.append(target)
            if video is not None:
                security.deliver(video, destination)
        except Exception:
            for target in reversed(published):
                backup = backups[target]
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    security.deliver(backup, target)
            raise


def export_once(destination: Path, binding: dict, generate, verify, current, *, directory: Path | None = None) -> Path:
    """生成先持久化再验收；验收失败保留昂贵候选。交付只复制，不编码。"""
    directory = directory or destination.parent
    destination.parent.mkdir(parents=True, exist_ok=True)
    key = fingerprint(binding)
    with _lock(directory):
        record = read_record(directory)
        receipt = directory / "candidates" / f"{key}.delivery.json"
        if record.get("key") != key and receipt.is_file():
            try:
                value = json.loads(receipt.read_text(encoding="utf-8"))
                record = value if isinstance(value, dict) else {}
            except (OSError, ValueError):
                record = {}
        source = Path(record.get("path", ""))
        valid = record.get("key") == key and source.is_file() and digest(source) == record.get("sha256")
        if not valid and record.get("key") == key:
            delivered = Path(record.get("destination", str(destination)))
            if delivered.is_file() and digest(delivered) == record.get("sha256"):
                source = directory / "candidates" / f"{key}.mp4"
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(delivered, source)
                for suffix in (".provenance.json", ".performance.json"):
                    if delivered.with_suffix(suffix).is_file():
                        shutil.copyfile(delivered.with_suffix(suffix), source.with_suffix(suffix))
                record["path"] = str(source.resolve())
                valid = True

        if not valid:
            source = directory / "candidates" / f"{key}.mp4"
            source.parent.mkdir(parents=True, exist_ok=True)
            try:
                generate(source)
            except Exception as exc:
                # 视频已落盘但报告/旁车写入失败时，仍保留可验收候选，不能再次全片生成。
                if source.is_file() and current() == binding:
                    record = {**binding, "key": key, "path": str(source.resolve()),
                              "sha256": digest(source), "status": "candidate-pending", "error": str(exc)}
                    _save(receipt, record)
                    _save(directory / "delivery.json", record)
                    logger.warning("完整候选已保存，后续操作失败；重试将复用：%s", source)
                raise
            if current() != binding:
                source.unlink(missing_ok=True)
                raise M2VError("生成期间输入变化，已丢弃候选；请重新 prepare")
            record = {**binding, "key": key, "path": str(source.resolve()),
                      "sha256": digest(source), "status": "candidate-pending"}
            _save(receipt, record)
            _save(directory / "delivery.json", record)
        else:
            logger.info("复用完整候选，不重新渲染：%s", source)
        try:
            record["status"] = "candidate-pending"
            _save(directory / "delivery.json", record)
            verify(source)
            # 统一溯源包含完整绑定；类型旁车若因上次 I/O 失败缺失，也可从固定输入重建。
            provenance_path = source.with_suffix(".provenance.json")
            try:
                provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                provenance = {"schemaVersion": 1}
            provenance["candidate"] = {**binding, "key": key, "sha256": record["sha256"]}
            _save(provenance_path, provenance)
            if current() != binding:
                raise M2VError("验收期间输入变化，未交付候选；请重新 prepare")
            record.update(status="ready", error=None)
            _save(directory / "delivery.json", record)
            _publish(source, destination, record["sha256"])
            record.update(status="delivered", destination=str(destination.resolve()))
            _save(directory / "delivery.json", record)
        except Exception as exc:
            record.update(status="validation-failed" if record["status"] != "ready" else "delivery-failed", error=str(exc))
            _save(directory / "delivery.json", record)
            raise
    return destination


def binding(root: Path, prepared: dict, parameters: dict) -> dict:
    """只绑定作品自己的实现；主项目检查器升级不改变媒体输入身份。"""
    if any(not isinstance(prepared.get('inputs', {}).get(k), str) for k in ('implementation', 'renderer')):
        raise M2VError('准备记录缺少本地实现绑定；请重新prepare')
    return {"preparedFingerprint": prepared["preparedFingerprint"], "parameters": parameters,
            "type": prepared.get("type"), "frames": prepared["durationInFrames"],
            "width": prepared["width"], "height": prepared["height"], "fps": prepared["fps"],
            "implementation": prepared['inputs']['implementation'],
            "renderer": prepared['inputs']['renderer']}
