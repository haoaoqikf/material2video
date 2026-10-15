"""检索、下载与留证：把在线图库的候选变成作品目录里可核验的本地素材。

这一层只做四件事，且顺序固定：

1. 按幕关键词检索候选（每幕独立查询，任一幕没有候选即整体失败）；
2. 用声明关键词与媒体元数据做**确定性**排序与去重（不使用随机、不读当前时间）；
3. 把入选素材下载到作品 ``assets/stock/``，文件名由来源与来源 ID 派生；
4. 写出 ``outputs/footage-search.json``：来源页、作者、许可、尺寸、时长与内容摘要。

检索记录绑定当前 brief 的检索指纹，因此改关键词或检索参数后记录立即过期。
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.types.stock import brief as brief_module
from m2v.types.stock import provider as provider_module

RECORD_VERSION = 1

#: 记录里保留的候选数量上限：只留证据，不留整份图库响应。
MAX_RECORDED_CANDIDATES = 20

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def search_fingerprint(brief: dict[str, Any]) -> str:
    """影响检索结果的字段摘要：主题、逐幕关键词与媒体偏好、图库参数。"""
    return fingerprint({
        "topic": brief["topic"],
        "provider": brief["provider"],
        "scenes": [{"id": scene["id"], "keywords": scene["keywords"],
                    "media": scene.get("media"), "assetId": scene.get("assetId")}
                   for scene in brief["scenes"]],
    })


def record_path(root: Path) -> Path:
    return root / brief_module.SEARCH_RECORD


def _score(candidate: provider_module.Candidate, keywords: list[str], kind_rank: int,
           config: dict[str, Any], portrait: bool) -> tuple:
    """确定性排序键：关键词命中优先，其次方向、分辨率与时长适配，最后来源 ID。"""
    text = candidate.description.lower()
    hits = sum(1 for word in keywords if word.lower() in text)
    orientation_fit = 1 if (candidate.height >= candidate.width) == portrait else 0
    target = 1920 if portrait else 1080
    resolution = min(candidate.height, target) / target if candidate.height else 0.0
    if candidate.kind == "video":
        duration = candidate.duration_seconds or 0.0
        in_range = 1 if config["minClipSeconds"] <= duration <= config["maxClipSeconds"] else 0
    else:
        in_range = 1
    return (-hits, -orientation_fit, -in_range, -resolution, kind_rank, candidate.id)


def _download(provider, candidate, destination: Path, timeout_s: float) -> tuple[str, int]:
    """下载到临时文件后按内容决定是否替换，重复检索不会无谓改动已有素材。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".m2v-stock-", dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name
        provider.download(candidate, staged, timeout_s)
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        size = staged.stat().st_size
        if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
            return digest, size
        staged.replace(destination)
    return digest, size


def search(root: Path, project: dict[str, Any], *, transport=None,
           timeout_s: float = provider_module.DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """执行一次完整检索并写出记录；任何一幕失败都不落盘部分结果。"""
    brief = brief_module.load(root, project)
    config = brief["provider"]
    adapter = provider_module.build(config, transport, cache_dir=root / "outputs/stock-cache")
    portrait = config["orientation"] in {"portrait", "square"}
    # 先取一次凭据：缺凭据时在任何请求与写盘之前失败。
    adapter.headers()
    used: set[str] = set()
    scenes: list[dict[str, Any]] = []
    for scene in brief["scenes"]:
        query = " ".join(scene["keywords"])
        kinds = [scene["media"]] if scene.get("media") else list(config["media"])
        found: list[tuple[tuple, provider_module.Candidate]] = []
        for rank, kind in enumerate(kinds):
            for candidate in adapter.search(query, kind, config["perPage"], timeout_s):
                if scene.get("assetId") is not None and candidate.id != str(scene["assetId"]):
                    continue
                if not config["allowReuse"] and candidate.id in used:
                    continue
                if not candidate.source_url or not candidate.author or not candidate.license:
                    continue
                found.append((_score(candidate, scene["keywords"], rank, config, portrait), candidate))
        if not found:
            raise M2VError(
                f"幕 {scene['id']} 没有可用候选：关键词「{query}」在 {config['name']} 未返回可采用的素材；"
                f"请调整关键词或放宽 provider.media/orientation 后重试")
        found.sort(key=lambda item: item[0])
        chosen = found[0][1]
        used.add(chosen.id)
        name = _UNSAFE_NAME.sub("-", f"{config['name']}-{chosen.kind}-{chosen.id}") + chosen.suffix
        relative = f"{brief_module.ASSET_DIR}/{name}"
        digest, size = _download(adapter, chosen, root / relative, timeout_s)
        scenes.append({
            "id": scene["id"], "keywords": list(scene["keywords"]), "query": query,
            "asset": {**chosen.to_json(), "path": relative, "sha256": digest, "bytes": size},
            "candidates": [candidate.to_json() for _key, candidate in found[:MAX_RECORDED_CANDIDATES]],
        })
    record = {"schemaVersion": RECORD_VERSION, "briefFingerprint": search_fingerprint(brief),
              "provider": {"name": config["name"], "apiBase": config["apiBase"],
                           "orientation": config["orientation"], "perPage": config["perPage"],
                           "media": list(config["media"])},
              "topic": brief["topic"], "scenes": scenes}
    target = record_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return record


def load_record(root: Path, project: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    """读取并复核检索记录：指纹、逐幕对应、素材文件与许可留证。"""
    path = record_path(root)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"缺少有效检索记录；请先执行 m2v stock search：{exc}") from exc
    if not isinstance(record, dict) or record.get("schemaVersion") != RECORD_VERSION:
        raise M2VError(f"{brief_module.SEARCH_RECORD} schemaVersion 必须为 {RECORD_VERSION}")
    if record.get("briefFingerprint") != search_fingerprint(brief):
        raise M2VError("检索记录与当前 brief.json 不一致；请重新执行 m2v stock search")
    config = brief["provider"]
    expected_provider = {"name": config["name"], "apiBase": config["apiBase"],
                         "orientation": config["orientation"], "perPage": config["perPage"],
                         "media": list(config["media"])}
    if record.get("provider") != expected_provider:
        raise M2VError("检索记录的图库参数与当前 brief.json 不一致；请重新执行 m2v stock search")
    entries = record.get("scenes")
    if not isinstance(entries, list) or [entry.get("id") for entry in entries] != [scene["id"] for scene in brief["scenes"]]:
        raise M2VError("检索记录的幕与当前 brief.json 不一致；请重新执行 m2v stock search")
    for entry, scene in zip(entries, brief["scenes"]):
        if entry.get("keywords") != list(scene["keywords"]):
            raise M2VError(f"幕 {scene['id']} 的关键词与检索记录不一致；请重新执行 m2v stock search")
        _verify_asset(root, scene["id"], entry.get("asset"))
    return record


def _verify_asset(root: Path, scene_id: str, asset: Any) -> None:
    if not isinstance(asset, dict):
        raise M2VError(f"幕 {scene_id} 的检索记录缺少素材")
    for field in ("sourceUrl", "author", "license"):
        if not isinstance(asset.get(field), str) or not asset[field].strip():
            raise M2VError(f"幕 {scene_id} 的素材缺少{field}；来源与许可必须留证")
    if asset.get("kind") not in {"video", "photo"}:
        raise M2VError(f"幕 {scene_id} 的素材类型无效：{asset.get('kind')!r}")
    for field in ("width", "height"):
        if type(asset.get(field)) is not int or asset[field] <= 0:
            raise M2VError(f"幕 {scene_id} 的素材 {field} 必须是正整数")
    if asset["kind"] == "video" and not (isinstance(asset.get("durationSeconds"), (int, float))
                                         and not isinstance(asset.get("durationSeconds"), bool)
                                         and asset["durationSeconds"] > 0):
        raise M2VError(f"幕 {scene_id} 的视频素材缺少有效时长")
    reference = asset.get("path")
    if not isinstance(reference, str) or not reference:
        raise M2VError(f"幕 {scene_id} 的素材缺少路径")
    target = (root / reference).resolve()
    if target != root.resolve() and root.resolve() not in target.parents:
        raise M2VError(f"素材路径越出作品目录：{reference}")
    if not target.is_file():
        raise M2VError(f"素材文件缺失：{reference}；请重新执行 m2v stock search")
    if hashlib.sha256(target.read_bytes()).hexdigest() != asset.get("sha256"):
        raise M2VError(f"素材文件与检索记录不一致：{reference}；请重新执行 m2v stock search")
