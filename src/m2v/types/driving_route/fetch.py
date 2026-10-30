"""``m2v driving-route fetch``：在线取得真实高速优先路线并原子保存。

流程刻意分成四步：先校验请求（含使用依据），再读 Key 并定位两个端点，然后按
高速优先规划路线，最后用离线校验同一套规则校验结果并原子替换 ``route.json``。
任一步失败都不发布半份材料，旧路线保持不变。

Key 只存在于本次进程的请求参数里；不写入材料、日志、异常或临时文件。
"""
from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.types.driving_route import materials
from m2v.types.driving_route.amap import AmapClient, Transport, default_transport

#: 唯一允许的凭据来源。
KEY_ENV = "M2V_AMAP_KEY"


def _request_document(root: Path) -> dict[str, Any]:
    return materials.load_request(root)


def _acquisition(request: dict[str, Any], origin: dict[str, Any],
                 destination: dict[str, Any], now: datetime) -> dict[str, Any]:
    timestamp = now if now.tzinfo is not None else now.astimezone()
    origin_point = f"{origin['location'][0]},{origin['location'][1]}"
    destination_point = f"{destination['location'][0]},{destination['location'][1]}"
    return {
        "provider": "amap",
        "service": "webservice",
        "apiVersion": "v5",
        "strategy": 34,
        "requestedAt": timestamp.isoformat(timespec="seconds"),
        "requests": [
            {"path": "/v3/geocode/geo",
             "params": {"address": request["origin"]["address"], "city": request["origin"]["city"],
                        "output": "JSON"}},
            {"path": "/v3/geocode/geo",
             "params": {"address": request["destination"]["address"],
                        "city": request["destination"]["city"], "output": "JSON"}},
            {"path": "/v5/direction/driving",
             "params": {"origin": origin_point, "destination": destination_point,
                        "strategy": "34", "show_fields": "cost,cities,polyline"}},
        ],
    }


def _route_document(request: dict[str, Any], origin: dict[str, Any],
                    destination: dict[str, Any], path: dict[str, Any],
                    now: datetime) -> dict[str, Any]:
    return {
        "schemaVersion": 2,
        "requestDigest": materials.request_digest(request),
        "coordinateSystem": "GCJ-02",
        "origin": origin,
        "destination": destination,
        "route": {
            "distanceMeters": path["distanceMeters"],
            "startPoint": path["startPoint"],
            "endPoint": path["endPoint"],
            "steps": path["steps"],
        },
        "cost": path["cost"],
        "cities": path["cities"],
        "acquisition": _acquisition(request, origin, destination, now),
        "sourceUsage": deepcopy(request["sourceUsage"]),
    }


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    """同目录唯一临时文件 + 原子替换；并发取数不会共用同一个临时文件。"""
    descriptor, name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _check_city(place: dict[str, Any], requested: dict[str, Any], label: str) -> None:
    if not materials.same_city(place["city"], requested["city"]):
        raise M2VError(f"{label}定位城市 {place['city']!r} 与请求城市 {requested['city']!r} 不一致；"
                       "请核对地址后重试")


def fetch(project_dir: str | Path, *, transport: Transport | None = None,
          now: datetime | None = None, api_base: str | None = None,
          timeout: float | None = None) -> Path:
    """取得并保存与当前请求绑定的真实路线；失败不破坏已有材料。"""
    root, project = load_project(project_dir)
    if project["type"] != "driving-route":
        raise M2VError("m2v driving-route fetch 仅适用于 driving-route 作品")
    if project.get("materials") != materials.MATERIALS:
        raise M2VError("driving-route 材料入口固定为 request.json、route.json")

    # 使用依据是取数前置条件：未落实时连网络都不发起。
    request = _request_document(root)
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise M2VError(f"缺少地图凭据：请设置环境变量 {KEY_ENV}；凭据不写入作品")

    client = AmapClient(
        key,
        api_base=api_base or "https://restapi.amap.com",
        timeout=timeout if timeout is not None else 30.0,
        transport=transport or default_transport,
    )
    origin = client.geocode(request["origin"]["address"], request["origin"]["city"])
    _check_city(origin, request["origin"], "起点")
    destination = client.geocode(request["destination"]["address"], request["destination"]["city"])
    _check_city(destination, request["destination"], "终点")
    path = client.drive(tuple(origin["location"]), tuple(destination["location"]))  # type: ignore[arg-type]

    document = _route_document(request, origin, destination, path, now or datetime.now().astimezone())
    materials.validate_route_document(request, document)

    # 联网期间请求文件可能被修改；落盘前复核，避免保存一份绑定旧请求的路线。
    current = materials.load_request(root)
    if materials.request_digest(current) != document["requestDigest"]:
        raise M2VError("取数期间 request.json 已变化；未保存路线，请重新执行 fetch")

    target = root / materials.MATERIALS["route"]
    _write_atomic(target, document)
    return target
