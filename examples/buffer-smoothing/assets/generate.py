"""生成原创 CC0 合成音乐床；无第三方采样。"""
import math
import struct
import wave
from pathlib import Path

def write(name, seconds, signal):
    path = Path(__file__).parent / name
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        for offset in range(0, int(seconds * 24000), 24000):
            out.writeframes(b''.join(struct.pack('<h', round(max(-1, min(1, signal(n / 24000))) * 32767)) for n in range(offset, min(int(seconds * 24000), offset + 24000))))

if __name__ == '__main__':
    write('bed.wav', 8, lambda t: .18 * (math.sin(2 * math.pi * 220 * t) + .5 * math.sin(2 * math.pi * 330 * t)) * (.75 + .25 * math.cos(2 * math.pi * t / 8)))
