"""母版来源反映真实WAV头，不能把已混音声道数写成旁白常量。"""
import importlib
import wave

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
