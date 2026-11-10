"""量测行程旁白并登记实际帧数；音色选择仍由制作助手依据完整文本完成。"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from film_runtime.engine import rhythm, tts

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    target = ROOT / 'scenes/journey-plan.json'
    plan = json.loads(target.read_text(encoding='utf-8'))
    project = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    texts = [station['text'] for station in plan['stations']]
    # 完整旁白改变时先按既有契约重选/重判音色，不能让量测工具伪造选择理由。
    actual = tts.preparation(project, texts)
    settings = tts.settings(project)
    speech = rhythm.configure(settings['speech']) if settings.get('speech') else None
    for station in plan['stations']:
        _, _, _, seconds, hit = tts.scene_audio(
            station['text'], actual['voice'], actual['rate'], ROOT / 'outputs/audio-cache',
            contract_version=9, rhythm=speech)
        station['frames'] = math.ceil(seconds * plan['fps'])
        logging.info('%s：%d帧，%.3f秒，缓存%s', station['body'], station['frames'], seconds, hit)
    plan['measurement'] = {'narrationSha256': tts.narration_digest(texts),
                           'voice': actual['voice'], 'rate': actual['rate'],
                           'speech': settings.get('speech')}
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    logging.info('旁白合计 %.3f 秒', sum(station['frames'] for station in plan['stations']) / plan['fps'])


if __name__ == '__main__':
    main()
