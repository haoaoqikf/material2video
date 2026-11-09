"""按固定配方恢复原创音效；摘要漂移拒绝，已有不同文件不覆盖。"""
import hashlib
import json
import logging
import shutil
import tempfile
import wave
from pathlib import Path
from synthesize import generate
from mint_synthesize import generate as generate_mint

HERE = Path(__file__).resolve().parent
log = logging.getLogger(__name__)


def validate(path: Path, item: dict) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['expectedSha256']:
        raise ValueError(f"音效摘要不符：{item['id']}")
    with wave.open(str(path)) as wav:
        if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth()) != (24000,1,2):
            raise ValueError(f"音频规格不符：{item['id']}")
        if abs(wav.getnframes()/24000-item['durationSeconds']) > 1/24000:
            raise ValueError(f"音效时长不符：{item['id']}")


def restore() -> None:
    recipe=json.loads((HERE/'recipe.json').read_text(encoding='utf-8'))
    if recipe.get('schemaVersion') != 1:
        raise ValueError('配方版本不符')
    pending=[]
    for item in recipe['assets']:
        target=(HERE.parent/item['path']).resolve()
        if not target.is_relative_to((HERE/'media').resolve()):
            raise ValueError('音效路径越界')
        if target.exists():
            validate(target,item)
            log.info('缓存命中：%s',item['id'])
        else:
            pending.append((item,target))
    with tempfile.TemporaryDirectory(prefix='compound-sound-') as tmp:
        staged=[]
        for item,target in pending:
            source=Path(tmp)/(item['id']+'.wav')
            if item['source'] == 'assets/mint_synthesize.py':
                generate_mint(item['id'],source)
            elif item['source'] == 'assets/synthesize.py':
                generate(item['id'],source)
            else:
                raise ValueError(f"未知本例音效生成源：{item['source']}")
            validate(source,item)
            staged.append((source,target))
        for source,target in staged:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out,source.open('rb') as inp:
                shutil.copyfileobj(inp,out)
            log.info('恢复完成：%s',target.name)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    restore()
