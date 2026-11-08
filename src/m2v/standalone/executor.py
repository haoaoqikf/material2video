"""委托作品本地命令并复核结果；主项目不注入渲染实现。"""
from __future__ import annotations

from collections import deque
import hashlib
import json
import logging
from pathlib import Path
import re
import threading

from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared
from .protocol import command
from .process import run

logger = logging.getLogger(__name__)
PREFIX = '__VIDEO_RESULT__'
STATES = {'validate': {'pass'}, 'prepare': {'prepared'}, 'inspect': {'current'},
          'preview': {'candidate'}, 'render': {'candidate'}, 'sample': {'captured'},
          'qa': {'pass', 'fail'}, 'build': {'built'}, 'setup': {'ready'}}


def local_artifact(root: Path, reference: str) -> Path:
    if (not isinstance(reference, str) or not reference or '\0' in reference or '\\' in reference
            or Path(reference).anchor or ':' in reference or '..' in Path(reference).parts):
        raise M2VError('作品执行结果必须使用作品内相对路径')
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise M2VError(f'作品执行结果缺失或越界：{reference}')
    return path


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise M2VError(f'缺少有效作品产物记录：{path.name}：{exc}') from exc
    if not isinstance(value, dict):
        raise M2VError(f'作品产物记录必须为对象：{path.name}')
    return value


def _execute(root: Path, project: dict, action: str, arguments: list[str] | None = None, *,
             timeout: float = 3600, cancelled: threading.Event | None = None) -> tuple[dict, dict | None]:
    if action not in STATES:
        raise M2VError(f'不支持的作品委托命令：{action}')
    argv = command(root, project, required=True)
    messages = []
    tail = deque(maxlen=20)

    def observe(line):
        if line.startswith(PREFIX):
            try:
                messages.append(json.loads(line[len(PREFIX):]))
            except ValueError as exc:
                raise M2VError('作品执行协议结果不是有效JSON') from exc
        elif line:
            tail.append(line)
            logger.info('%s', line)

    logger.info('使用作品本地入口执行 %s：%s', action, root)
    code = run([*argv, action, *(arguments or [])], root, timeout=timeout,
               on_line=observe, cancelled=cancelled)
    if code != 0 and not (action == 'qa' and code == 1):
        raise M2VError(f'作品本地{action}失败（退出码{code}）：' + '\n'.join(tail))
    if len(messages) != 1:
        raise M2VError('作品执行缺少唯一的有效结果记录，不能仅凭退出码认定成功')
    message = messages[0]
    if (not isinstance(message, dict) or set(message) != {'version', 'command', 'result'}
            or type(message['version']) is not int or message['version'] != 1
            or message['command'] != action or not isinstance(message['result'], dict)):
        raise M2VError('作品执行协议版本、命令或结果结构不符')
    result = message['result']
    prepared = None
    if not isinstance(result.get('status'), str) or result['status'] not in STATES[action]:
        raise M2VError('作品执行结果状态与命令不符')
    if not isinstance(result.get('environment'), dict) or not result['environment']:
        raise M2VError('作品执行结果缺少环境记录')
    if action == 'qa' and code != (1 if result['status'] == 'fail' else 0):
        raise M2VError('作品QA结果与退出码不符')
    if action in {'prepare', 'inspect', 'preview', 'render', 'sample', 'qa'}:
        artifact = local_artifact(root, result.get('path'))
        expected = result.get('sha256')
        with artifact.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or actual != expected:
            raise M2VError('作品执行结果文件摘要不符，拒绝绑定')
    if action in {'prepare', 'inspect'}:
        if result['path'] != 'outputs/prepared.json':
            raise M2VError('准备记录必须位于outputs/prepared.json')
        prepared = load_current_prepared(root, project)
        if result.get('preparedFingerprint') != prepared['preparedFingerprint']:
            raise M2VError('作品自报准备身份与实际记录不符')
    return result, prepared


def execute(root: Path, project: dict, action: str, arguments: list[str] | None = None, *,
            timeout: float = 3600, cancelled: threading.Event | None = None) -> dict:
    return _execute(root, project, action, arguments, timeout=timeout, cancelled=cancelled)[0]


def prepare(root: Path, project: dict, arguments: list[str]) -> dict:
    return _execute(root, project, 'prepare', arguments)[1]


def current(root: Path, project: dict) -> dict:
    return _execute(root, project, 'inspect', timeout=120)[1]
