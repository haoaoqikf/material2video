"""真实委托进程必须隔离环境，并回收超时、取消及正常退出后的后代。"""
import json
import os
from pathlib import Path
import sys
import threading
import time

import psutil
import pytest

from m2v.core.errors import M2VError
from m2v.standalone.process import environment, run


def tree(root: Path, *, orphan: bool) -> list[str]:
    child = root / 'child.py'
    child.write_text("import os,time,pathlib\npathlib.Path('pid.json').write_text(str(os.getpid()))\n"
                     "print('child-ready',flush=True)\ntime.sleep(30)\n"
                     "pathlib.Path('late.txt').write_text('should not survive')\n", encoding='utf-8')
    parent = root / 'parent.py'
    parent.write_text("import subprocess,sys,pathlib,time\n"
                      "subprocess.Popen([sys.executable,'child.py'])\n"
                      "while not pathlib.Path('pid.json').exists(): time.sleep(.01)\n"
                      + ("print('parent-exit',flush=True)\n" if orphan else 'time.sleep(30)\n'), encoding='utf-8')
    return [sys.executable, str(parent)]


@pytest.mark.parametrize('mode', ['timeout', 'cancel', 'orphan'])
def test_entire_process_tree_is_gone_before_return(tmp_path, mode):
    cancel = threading.Event()
    lines = []
    def observe(line):
        lines.append(line)
        if mode == 'cancel' and line == 'child-ready':
            cancel.set()
    argv = tree(tmp_path, orphan=mode == 'orphan')
    start = time.monotonic()
    if mode == 'orphan':
        assert run(argv, tmp_path, timeout=8, on_line=observe) == 0
        assert 'parent-exit' in lines
    else:
        with pytest.raises(M2VError, match='超时' if mode == 'timeout' else '取消'):
            run(argv, tmp_path, timeout=1.5 if mode == 'timeout' else 8,
                on_line=observe, cancelled=cancel)
    pid = int((tmp_path / 'pid.json').read_text())
    assert not psutil.pid_exists(pid)
    assert not (tmp_path / 'late.txt').exists()
    assert time.monotonic() - start < 5


def test_log_callback_failure_also_cleans_tree(tmp_path):
    argv = tree(tmp_path, orphan=False)
    def observe(line):
        raise M2VError('invalid protocol')
    with pytest.raises(M2VError, match='protocol'):
        run(argv, tmp_path, timeout=8, on_line=observe)
    assert not psutil.pid_exists(int((tmp_path / 'pid.json').read_text()))


def test_environment_drops_main_dependencies_and_preserves_system_tools(tmp_path, monkeypatch):
    for key in ['PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS', 'VIRTUAL_ENV',
                'UV_PROJECT', 'UV_PROJECT_ENVIRONMENT', 'M2V_CONTENT_ROOT']:
        monkeypatch.setenv(key, 'main-project-value')
    env = environment(tmp_path)
    assert not set(['PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS',
                    'VIRTUAL_ENV', 'UV_PROJECT', 'M2V_CONTENT_ROOT']) & env.keys()
    assert env['UV_PROJECT_ENVIRONMENT'] == str(tmp_path / '.venv')
    assert env['PATH'].split(os.pathsep)[0] == str(tmp_path / '.venv' / ('Scripts' if os.name == 'nt' else 'bin'))
    assert env['PYTHONUTF8'] == '1'
