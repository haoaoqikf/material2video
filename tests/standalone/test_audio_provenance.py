"""母版来源反映真实WAV头，不能把已混音声道数写成旁白常量。"""
import importlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest


@pytest.mark.parametrize('module_name', [
    'm2v.types.scene_film.explainer_render',
    'film_runtime.types.scene_film.explainer_render',
])
@pytest.mark.parametrize('channels,rate', [(1, 24000), (2, 24000), (2, 48000)])
def test_master_audio_provenance_reads_actual_header(tmp_path, module_name, channels, rate):
    module = importlib.import_module(module_name)
    source = tmp_path / 'master.wav'
    with wave.open(str(source), 'wb') as stream:
        stream.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(bytes(channels * 2 * 16))
    assert module._master_audio_metadata(source) == {
        'masterSampleRate': rate, 'masterChannels': channels,
    }


@pytest.mark.parametrize('channels,rate', [(1, 24000), (2, 24000), (2, 48000)])
def test_solar_runtime_audio_provenance_isolated(tmp_path, channels, rate):
    """独立子进程确保检查示例本身，不误命中已导入的模板包。"""
    runtime = Path(__file__).resolve().parents[2] / 'examples/spatial-3d/solar-system-journey/runtime/python'
    source = tmp_path / 'master.wav'
    with wave.open(str(source), 'wb') as stream:
        stream.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(bytes(channels * 2 * 16))
    result = subprocess.run([
        sys.executable, '-c',
        'import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
        'from film_runtime.types.scene_film import explainer_render as module; '
        'assert Path(module.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve()); '
        'print(json.dumps(module._master_audio_metadata(Path(sys.argv[2]))))',
        str(runtime), str(source),
    ], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'masterSampleRate': rate, 'masterChannels': channels}
