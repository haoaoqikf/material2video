"""从固定NASA Saturn GLB提取原图和本例几何；不是通用glTF导入器。"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

SOURCE_URL = 'https://science.nasa.gov/resource/saturn-3d-model/'
ARCHIVE_URL = 'https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/s/Saturn_1_120536.glb'
ARCHIVE_SHA256 = '8dbfde533b13e938408d8aded1d1ce48a084806233f67775371d83013dba7d38'
IMAGE_SHA256 = '2b4628833c2610ac6677f729376c00440a6bc4df4f85b4928519179e37536f4b'


def model(data):
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('NASA Saturn原包摘要不符')
    if len(data) < 28 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('不支持的GLB头或长度')
    cursor = 12
    chunks = []
    while cursor < len(data):
        if cursor + 8 > len(data):
            raise ValueError('GLB chunk头被截断')
        size, kind = struct.unpack_from('<II', data, cursor)
        cursor += 8
        if size % 4 or cursor + size > len(data):
            raise ValueError('GLB chunk越界或未对齐')
        chunks.append((kind, data[cursor:cursor + size]))
        cursor += size
    if [x[0] for x in chunks] != [0x4E4F534A, 0x004E4942]:
        raise ValueError('仅支持JSON/BIN两个GLB chunk')
    doc = json.loads(chunks[0][1])
    binary = chunks[1][1]
    if (doc['asset']['version'] != '2.0' or doc.get('extensionsRequired')
            or len(doc['buffers']) != 1 or 'uri' in doc['buffers'][0]
            or not 0 <= len(binary) - doc['buffers'][0]['byteLength'] <= 3
            or any('sparse' in a for a in doc['accessors'])
            or any('extensions' in p for m in doc['meshes'] for p in m['primitives'])
            or any(k in doc['nodes'][0] for k in ('matrix', 'translation', 'rotation', 'scale'))
            or doc['nodes'][0]['mesh'] != 0):
        raise ValueError('固定提取器不支持外部buffer、稀疏/压缩或节点变换')
    return doc, binary


def view(doc, binary, index):
    item = doc['bufferViews'][index]
    offset, size = item.get('byteOffset', 0), item['byteLength']
    if item.get('buffer', 0) != 0 or offset < 0 or size < 0 or offset + size > len(binary):
        raise ValueError('GLB bufferView越界')
    return binary[offset:offset + size], item


def saturn_image(data):
    doc, binary = model(data)
    image = doc['images'][0]
    if image.get('mimeType') != 'image/png' or 'uri' in image:
        raise ValueError('NASA Saturn原图须为嵌入PNG')
    raw, _ = view(doc, binary, image['bufferView'])
    if hashlib.sha256(raw).hexdigest() != IMAGE_SHA256:
        raise ValueError('NASA Saturn原图摘要不符')
    return raw


def geometry(data):
    doc, binary = model(data)
    primitive = doc['meshes'][0]['primitives'][0]
    if primitive.get('mode', 4) != 4 or 'targets' in primitive:
        raise ValueError('仅支持固定三角形网格')

    def read(index, kind, component):
        item = doc['accessors'][index]
        if item['type'] != kind or item['componentType'] != component or item.get('normalized'):
            raise ValueError('不支持的几何accessor')
        raw, source = view(doc, binary, item['bufferView'])
        count = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1}[kind]
        fmt = '<' + count * {5126: 'f', 5123: 'H'}[component]
        size = struct.calcsize(fmt)
        offset, stride, length = item.get('byteOffset', 0), source.get('byteStride', size), item['count']
        if length <= 0 or offset < 0 or stride < size or offset + (length - 1) * stride + size > len(raw):
            raise ValueError('几何accessor越界')
        result = [struct.unpack_from(fmt, raw, offset + i * stride) for i in range(length)]
        if any(not math.isfinite(v) for row in result for v in row):
            raise ValueError('几何含非有限值')
        return result

    attributes = primitive['attributes']
    positions = read(attributes['POSITION'], 'VEC3', 5126)
    normals = read(attributes['NORMAL'], 'VEC3', 5126)
    uv = read(attributes['TEXCOORD_0'], 'VEC2', 5126)
    indices = [row[0] for row in read(primitive['indices'], 'SCALAR', 5123)]
    if (len(positions) != len(normals) or len(positions) != len(uv) or len(indices) % 3
            or any(i >= len(positions) for i in indices)):
        raise ValueError('几何属性或三角索引不一致')
    return {
        'version': 1, 'sourceUrl': SOURCE_URL, 'archiveUrl': ARCHIVE_URL,
        'archiveSha256': ARCHIVE_SHA256, 'mesh': 0,
        'accessors': {**attributes, 'indices': primitive['indices']},
        'normalization': 500, 'flipV': True,
        'polarRatio': max(abs(p[1]) for p in positions) / 500,
        'positions': [[round(v / 500, 8) for v in p] for p in positions],
        'normals': [[round(v, 8) for v in p] for p in normals],
        # TextureLoader保留flipY=true；glTF UV只在此翻转一次。
        'uv': [[round(u, 8), round(1 - v, 8)] for u, v in uv],
        'triangles': [indices[i:i + 3] for i in range(0, len(indices), 3)],
    }


def geometry_text(value):
    """每顶点/三角一行，固定小数精度；保持数值JSON可审阅，不嵌入二进制。"""
    arrays = ('positions', 'normals', 'uv', 'triangles')
    head = {k: v for k, v in value.items() if k not in arrays}
    lines = [json.dumps(head, ensure_ascii=False, indent=2)[:-2] + ',']
    for key in arrays:
        lines.append(f'  "{key}": [')
        lines.append(',\n'.join('    ' + json.dumps(row, separators=(',', ':')) for row in value[key]))
        lines.append('  ]' + (',' if key != arrays[-1] else ''))
    return '\n'.join(lines) + '\n}\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--geometry', type=Path)
    parser.add_argument('--image', type=Path)
    args = parser.parse_args()
    data = args.model.read_bytes()
    text, image = geometry_text(geometry(data)), saturn_image(data)
    if args.geometry:
        args.geometry.parent.mkdir(parents=True, exist_ok=True)
        args.geometry.write_text(text, encoding='utf-8', newline='\n')
    if args.image:
        args.image.parent.mkdir(parents=True, exist_ok=True)
        args.image.write_bytes(image)
    print('NASA Saturn几何', hashlib.sha256(text.encode()).hexdigest(), '原图', IMAGE_SHA256)
