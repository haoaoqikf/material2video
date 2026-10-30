"""自驾路线测试夹具：合成请求、真实形状路线与作品目录。

合成坐标只用于验证几何与绑定，不写入任何首个作品；真实取数与首例另按制作
流程核验使用依据。
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from m2v.core.project import create_project
from m2v.types.driving_route import materials

FIXED_NOW = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))

ORIGIN = (121.4700, 31.2300)
MIDDLE = [(121.4800, 31.2400), (121.4900, 31.2500)]
DESTINATION = (121.5000, 31.2600)


def request_document() -> dict:
    return {
        "schemaVersion": 1,
        "origin": {"city": "上海市", "address": "上海市黄浦区合成起点", "label": "上海"},
        "destination": {"city": "上海市", "address": "上海市黄浦区合成终点", "label": "上海西"},
        "strategy": "highway-first",
        "durationSeconds": 30,
        "canvas": {"width": 1920, "height": 1080},
        "sourceUsage": {
            "verifiedOn": "2026-10-30",
            "documents": [{"title": "合成许可记录", "url": "https://example.invalid/license"}],
            "account": "合成测试账号范围",
            "purpose": "离线保存路线并制作二维动画视频",
            "offlineStorage": True,
            "derivativeFrames": True,
            "videoPublication": True,
            "attribution": "地图数据 © 高德地图（合成测试）",
        },
    }


def acquisition() -> dict:
    return {
        "provider": "amap",
        "service": "webservice",
        "apiVersion": "v5",
        "strategy": 34,
        "requestedAt": FIXED_NOW.isoformat(timespec="seconds"),
        "requests": [
            {"path": "/v3/geocode/geo",
             "params": {"address": "上海市黄浦区合成起点", "city": "上海市", "output": "JSON"}},
            {"path": "/v3/geocode/geo",
             "params": {"address": "上海市黄浦区合成终点", "city": "上海市", "output": "JSON"}},
            {"path": "/v5/direction/driving",
             "params": {"origin": "121.47,31.23", "destination": "121.5,31.26",
                        "strategy": "34", "show_fields": "polyline"}},
        ],
    }


def route_document(request: dict, *, steps: list[dict] | None = None,
                   origin_location=ORIGIN, destination_location=DESTINATION) -> dict:
    points = [list(ORIGIN), *[list(item) for item in MIDDLE], list(DESTINATION)]
    steps = steps if steps is not None else [
        {"road": "合成高速", "distanceMeters": 2500, "points": points[:3]},
        {"road": "合成高速", "distanceMeters": 2500, "points": points[2:]},
    ]
    return {
        "schemaVersion": 1,
        "requestDigest": materials.request_digest(request),
        "coordinateSystem": "GCJ-02",
        "origin": {
            "location": list(origin_location),
            "formattedAddress": "上海市黄浦区合成起点",
            "city": "上海市",
            "level": "兴趣点",
        },
        "destination": {
            "location": list(destination_location),
            "formattedAddress": "上海市黄浦区合成终点",
            "city": "上海市",
            "level": "兴趣点",
        },
        "route": {
            "distanceMeters": 5000,
            "startPoint": steps[0]["points"][0],
            "endPoint": steps[-1]["points"][-1],
            "steps": steps,
        },
        "acquisition": acquisition(),
        "sourceUsage": copy.deepcopy(request["sourceUsage"]),
    }


def write_project(tmp_path: Path, *, request: dict | None = None, route: dict | None = None,
                  output: dict | None = None) -> Path:
    root = tmp_path / "demo"
    create_project(root, "driving-route", materials.MATERIALS,
                   output={"width": 1920, "height": 1080, **(output or {})})
    request = copy.deepcopy(request) if request is not None else request_document()
    (root / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    if route is None:
        route = route_document(request)
    (root / "route.json").write_text(json.dumps(route, ensure_ascii=False), encoding="utf-8")
    return root


def edit(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
