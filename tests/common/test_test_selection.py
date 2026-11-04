"""用临时小套件验证选择行为，不启动真实媒体或浏览器。"""
from pathlib import Path

import pytest

pytest_plugins = ['pytester']


@pytest.mark.parametrize('arguments,expected', [
    (['test_sample.py'], {'test_fast'}),
    (['.'], {'test_fast'}),
    (['test_sample.py::test_media'], {'test_media[a]', 'test_media[b]'}),
    (['other', 'test_sample.py::test_media[a]'], {'test_fast', 'test_media[a]'}),
    (['test_sample.py', '-m', 'media'], {'test_media[a]', 'test_media[b]'}),
    (['test_sample.py', '--full'], {'test_fast', 'test_media[a]', 'test_media[b]', 'test_slow'}),
])
def test_cost_filter_respects_selected_scope(pytester, arguments, expected):
    pytester.makeconftest((Path(__file__).parents[1] / 'conftest.py').read_text(encoding='utf-8'))
    pytester.makeini('[pytest]\nmarkers =\n media: media\n slow: slow\naddopts = --strict-markers')
    pytester.makepyfile(test_sample='''
import pytest
def test_fast(): pass
@pytest.mark.media
@pytest.mark.parametrize('value', ['a', 'b'])
def test_media(value): pass
@pytest.mark.slow
def test_slow(): pass
''')
    if 'other' in arguments:
        other = pytester.mkdir('other')
        (other / 'test_other.py').write_text(
            'import pytest\ndef test_fast(): pass\n@pytest.mark.slow\ndef test_other_slow(): pass\n',
            encoding='utf-8',
        )
    result = pytester.runpytest('--collect-only', '-q', *arguments)
    assert result.ret == 0
    collected = {line.split('::', 1)[1] for line in result.stdout.lines if '.py::' in line}
    assert collected == expected
