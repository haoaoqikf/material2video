"""用现有合成导入器离线恢复事件音，固定摘要不符时拒绝覆盖。"""
from pathlib import Path
import hashlib
import json
import logging
import shutil
import tempfile

from m2v.core.project import _write_json
from m2v.types.general import sound_library

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def restore(root: Path = ROOT) -> None:
    assets = root / 'assets'
    manifest = json.loads((assets / 'sound-recipe.json').read_text(encoding='utf-8'))
    expected = json.loads((assets / 'sound-checks.json').read_text(encoding='utf-8'))
    expected_by_id = {item['id']: item for item in expected['assets']}
    if len(expected_by_id) != len(expected['assets']) or set(expected_by_id) != {a['id'] for a in manifest['assets']}:
        raise ValueError('声音配方与固定摘要清单不一致')
    # 先在隔离临时目录生成并核对整个批次；失败不更改已有登记或文件。
    with tempfile.TemporaryDirectory(prefix='luck-example-sound-') as name:
        staging = Path(name)
        record = sound_library.import_assets(staging, manifest, base=assets)
        for entry in record['assets']:
            check = expected_by_id[entry['id']]
            if any(entry[k] != check[k] for k in ('sha256', 'sampleRate', 'channels', 'frames', 'license')):
                raise ValueError(f"声音恢复摘要或规格不符：{entry['id']}")
            target = root / entry['path']
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != check['sha256']:
                raise ValueError(f"已有声音摘要不符，拒绝覆盖：{entry['id']}")
        for entry in record['assets']:
            target = root / entry['path']
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output, (staging / entry['path']).open('rb') as source:
                    shutil.copyfileobj(source, output)
            logger.info('已核对声音 %s (%s)', entry['id'], entry['sha256'])
        _write_json(root / sound_library.RECORD, record)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    restore()
