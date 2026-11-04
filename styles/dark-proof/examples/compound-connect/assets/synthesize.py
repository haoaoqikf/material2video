"""《接》原创声音v2：数学合成，无采样；24kHz PCM16 mono，CC0-1.0。

仅生成必要事件音，无旁白、无配乐或持续环境床。输出／经过回路／合并用稳定音色。
新媒体使用-v2文件名，不覆盖旧版或接受旧文件摘要漂移。
"""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
import wave
from array import array
from pathlib import Path

HERE=Path(__file__).resolve().parent
RATE=24000
DURATIONS={'emit-v2':.20,'travel-v2':.9,'merge-v2':.85,'land-v2':.6,'reveal-v2':1.4,'close-v2':2.3}


def tone(identity: str, seconds: float) -> array:
    values=array('d')
    for i in range(round(seconds*RATE)):
        t=i/RATE
        if identity=='travel-v2':
            phase=2*math.pi*(260*t+180*t*t)
            value=(math.sin(phase)+.25*math.sin(phase*1.5))*math.sin(math.pi*t/seconds)**2*.24
        else:
            base={'emit-v2':880,'merge-v2':440,'land-v2':220,'reveal-v2':110,'close-v2':220}[identity]
            env=min(1,t/.012)*math.exp(-t*(12 if identity=='emit-v2' else 3))
            value=(math.sin(2*math.pi*base*t)+.4*math.sin(2*math.pi*base*1.5*t)
                   +.15*math.sin(2*math.pi*base*2*t))*env*.20
            if identity in ('reveal-v2','close-v2'):
                value+=math.sin(2*math.pi*55*t)*min(1,t/.06)*math.exp(-t*2)*.16
        values.append(value*min(1,(seconds-t)/.06))
    return values



def generate(identity: str, target: Path) -> None:
    seconds=DURATIONS[identity]
    values=tone(identity,seconds)
    # 固定标度保留事件间的动态差；不逐文件拉满峰值。
    samples=array('h',(round(max(-.95,min(.95,x))*32767) for x in values))
    import sys
    if sys.byteorder!='little':samples.byteswap()
    with wave.open(str(target),'wb') as out:
        out.setparams((1,2,RATE,0,'NONE','not compressed'))
        out.writeframes(samples.tobytes())


def recipe() -> dict:
    definitions=DURATIONS
    assets=[]
    # 写配方时也遵守恢复规则：已有不同素材不覆盖，新增版本须换身份。
    with tempfile.TemporaryDirectory(prefix='connect-score-') as temp:
        for identity,seconds in definitions.items():
            staged=Path(temp)/(identity+'.wav');generate(identity,staged)
            digest=hashlib.sha256(staged.read_bytes()).hexdigest()
            destination=HERE/'media'/(identity+'.wav')
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:
                    raise ValueError(f'已有媒体摘要不同：{destination.name}；须显式使用新版本身份')
            else:destination.write_bytes(staged.read_bytes())
            assets.append({'id':identity,'path':f'assets/media/{identity}.wav','transform':'generate',
                           'durationSeconds':seconds,'sampleRateHz':RATE,'channels':1,'expectedSha256':digest,
                           'author':'material2video contributors','license':'CC0-1.0','source':'assets/synthesize.py'})
    result={'schemaVersion':1,'assets':assets}
    (HERE/'recipe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    print(json.dumps(recipe(),ensure_ascii=False,indent=2))
