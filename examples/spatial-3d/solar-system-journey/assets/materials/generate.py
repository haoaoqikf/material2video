"""原生分辨率艺术材质；不是地形测量或低分辨率图片插值。按 CC0 1.0 分发。

日间颜色仍使用登记的观测地图；本生成器提供气体流动/冰面微法线、粗糙度、
不自发光天体的零发光图，以及不透视地表的土卫六雾霾。
尺寸由像素采样位置直接计算，不读取或放大旧图片。地球法线和海面遮罩另取原作者地图。
"""
from __future__ import annotations

import argparse
import math
import struct
import zlib
from pathlib import Path

WIDTH, HEIGHT = 4096, 2048
TARGETS = ('sun', 'earth', 'jupiter', 'pluto', 'titan')


def png(path: Path, width: int, height: int, rows) -> None:
    """逐行压缩 RGBA，内存不随贴图面积积累；写完后才替换目标文件。"""
    temporary = path.with_suffix('.partial')
    def chunk(file, kind, payload):
        file.write(struct.pack('>I', len(payload)) + kind + payload)
        file.write(struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff))
    with temporary.open('wb') as file:
        file.write(b'\x89PNG\r\n\x1a\n')
        chunk(file, b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
        compressor = zlib.compressobj(6)
        count = 0
        for row in rows:
            if len(row) != width * 4:
                raise ValueError('材质行宽不符')
            data = compressor.compress(b'\0' + row)
            if data:
                chunk(file, b'IDAT', data)
            count += 1
        if count != height:
            raise ValueError('材质行数不符')
        chunk(file, b'IDAT', compressor.flush())
        chunk(file, b'IEND', b'')
    temporary.replace(path)


def material_rows(target: str, role: str, width=WIDTH, height=HEIGHT):
    """经度为整周期，极点扰动收敛；强度控制为微表面而不是虚构山脉。"""
    if role == 'emissive':
        # 不自发光天体必须为零；太阳/地球的发光图由已登记的日面/夜景地图提供。
        yield from (bytes([0, 0, 0, 255]) * width for _ in range(height))
        return
    frequency = {'sun': 53, 'earth': 23, 'jupiter': 31, 'pluto': 17, 'titan': 7}[target]
    longitudes = [(x + .5) / width * math.tau for x in range(width)]
    for y in range(height):
        latitude = ((y + .5) / height - .5) * math.pi
        pole = math.cos(latitude) ** 2
        row = bytearray()
        for longitude in longitudes:
            wave = math.sin(longitude * frequency + math.sin(latitude * 29) * 2)
            fine = math.cos(longitude * (frequency * 3) - latitude * 53)
            if role == 'normal':
                dx = (wave * .08 + fine * .025) * pole
                dy = math.sin(latitude * 67 + wave * 1.2) * .1 * pole
                length = math.sqrt(dx * dx + dy * dy + 1)
                row.extend((round(127.5 * (dx / length + 1)), round(127.5 * (dy / length + 1)),
                            round(127.5 * (1 / length + 1)), 255))
            elif role == 'roughness':
                value = round(255 * (.78 + .1 * wave * pole + .04 * fine))
                row.extend((value, value, value, 255))
            elif role == 'color' and target == 'titan':
                haze = .95 + .035 * wave * pole + .018 * fine
                row.extend((round(212 * haze), round(155 * haze), round(74 * haze), 255))
            else:
                raise ValueError(f'未知材质 {target}/{role}')
        yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        for role in ('normal', 'roughness', 'emissive'):
            if target == 'earth' or (target == 'sun' and role == 'emissive'):
                continue
            path = args.out / f'{target}-{role}.png'
            png(path, WIDTH, HEIGHT, material_rows(target, role))
            print(path.name, flush=True)
    png(args.out / 'titan-color.png', WIDTH, HEIGHT, material_rows('titan', 'color'))


if __name__ == '__main__':
    main()
