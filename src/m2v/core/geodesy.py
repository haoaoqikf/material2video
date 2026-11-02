"""球面距离的共享口径。

路线进度、段间连续性与端点容差都按同一颗球计算。用 `geographiclib` 的
零扁率球体（半径 6371008.8 米）表达，而不是再写一份 haversine：公式与
现有口径等价，同时把数值实现交给经过验证的库。
"""
from __future__ import annotations

from geographiclib.geodesic import Geodesic

#: 球面距离口径；只用于沿路进度与连续性判定，不冒充公路里程。
EARTH_RADIUS_METERS = 6371008.8

_GEODESIC = Geodesic(EARTH_RADIUS_METERS, 0.0)


def distance_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点间球面距离（米）；经纬度顺序为 (经度, 纬度)。"""
    return _GEODESIC.Inverse(a[1], a[0], b[1], b[0])["s12"]
