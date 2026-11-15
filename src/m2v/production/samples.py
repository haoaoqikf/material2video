"""原生样品凭据与交付；渲染可失败，交付必须证据完整且独立通过。"""
from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core import security
from m2v.engine import design_sample
from . import dependencies, issues, ledger, reuse
from .model import fields, identifier, now, text
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)
VERSION = 1


def capture(root: Path, project: dict, **options) -> dict:
    workflow = outputs(root) / 'production/workflow.json'
    if not workflow.exists():
        if list((outputs(root) / 'production').glob('*/cycle.json')):
            raise M2VError('已有周期记录但当前周期缺失；不能通过样品采集重置历史')
        ledger.start(root, project, basis='网页原生设计试制')
    cycle = ledger.cycle(root)
    if cycle['projectId'] != project['id']:
        raise M2VError('当前周期不属于本作品')
    identity = uuid.uuid4().hex
    relative = f'samples/{identity}'
    target = local(outputs(root), relative + '/capture.json', exists=False).parent
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sample-', dir=target.parent) as temporary:
        stage = Path(temporary) / 'capture'
        stage.mkdir()
        # 编码器在私有目录内完成中间发布；整包移到最终位置后统一递归修复与自检。
        with security.private_staging(stage):
            result = design_sample.render(root, project, stage, **options)
        artifacts = {path.relative_to(stage).as_posix(): dependencies.digest(path)
                     for path in stage.rglob('*') if path.is_file() and path != stage / 'capture.json'}
        value = {'version': VERSION, 'id': identity, 'cycleId': cycle['cycleId'], 'createdAt': now(),
                 **result, 'artifacts': artifacts}
        write(stage / 'capture.json', value)
        request = {'version': 2, 'round': 'trial', 'fps': value['fps'], 'items': review_items(value),
                   'sources': [f'outputs/{relative}/capture.json', value['entry']], 'sceneIds': [],
                   'displaySizes': sorted({value['width'], 393}), 'references': [], 'conditions': []}
        write(stage / 'review-request.json', request)
        # 唯一ID不覆盖历史；事件收据是入口，手填capture.json不能成为有效采集。
        security.deliver_directory(stage, target)
    record = receipt(outputs(root), target / 'capture.json')
    ledger.append(root, project, 'sample-captured', data={'sampleId': identity, 'receipt': record})
    logger.info('原生样品 %s 已采集；尚未通过独立评审，不可交付', identity)
    return {'id': identity, 'capture': record['path'], 'request': str(target / 'review-request.json'),
            'webCommand': f'm2v sample serve --project "{root}" --id {identity}', 'reviewed': False}


def review_items(value: dict) -> list[dict]:
    prefix = f"samples/{value['id']}/"
    return [{'id': f'still-{row["frame"]}', 'path': prefix + row['path'], 'window': [0, 1], 'dynamic': False}
            for row in value['stills']] + [
        {'id': 'motion', 'path': prefix + value['video'], 'window': [0, value['durationInFrames']], 'dynamic': True}]


def scope_sources(root: Path, request: dict) -> list[str]:
    """复查范围使用稳定身份，报告绑定仍保留每次采集的独立凭据和实际摘要。

    这里只验历史采集锚点，不验旧源码是否仍当前；修复后的源码本就应不同。
    通用图片或删减过程的请求不能获得原生范围身份。
    """
    sources = request['sources']
    events, errors = ledger.history(root)
    if errors:
        raise M2VError('; '.join(errors))
    for event in events:
        if event['type'] != 'sample-captured':
            continue
        record = event['data']['receipt']
        source = 'outputs/' + record['path']
        if source not in sources or not ledger.evidence_valid(root, [record]):
            continue
        value = read(local(outputs(root), record['path']))
        if (request['items'] == review_items(value) and request['fps'] == value['fps']
                and value['entry'] in sources):
            identity = f"native-sample:{value['fps']}:{value['width']}x{value['height']}:{value['entry']}"
            return [identity if item == source else item for item in sources]
    return sources


def load(root: Path, project: dict, identity: str) -> tuple[dict, Path]:
    identifier(identity)
    events, errors = ledger.history(root)
    if errors:
        raise M2VError('; '.join(errors))
    matches = [event for event in events if event['type'] == 'sample-captured'
               and event['data'].get('sampleId') == identity]
    if len(matches) != 1 or not ledger.evidence_valid(root, [matches[0]['data']['receipt']]):
        raise M2VError('缺少有效原生采集事件或凭据已改变；不能使用外部图片代替样品')
    path = local(outputs(root), matches[0]['data']['receipt']['path'])
    if path.relative_to(outputs(root)).as_posix() != f'samples/{identity}/capture.json':
        raise M2VError('样品凭据位置不符')
    value = read(path)
    fields(value, {'version', 'id', 'cycleId', 'createdAt', 'artifacts'} | design_sample.RESULT_FIELDS)
    if (value['version'] != VERSION or value['id'] != identity
            or value['cycleId'] != ledger.cycle(root)['cycleId']
            or value['project'] != {k: project.get(k) for k in ('id', 'type', 'output')}):
        raise M2VError('原生样品属于旧周期、旧格式或作品配置已经改变')
    if not value['inputs'] or not value['artifacts']:
        raise M2VError('原生样品缺少输入或产物绑定')
    for label, digest in value['inputs'].items():
        if dependencies.digest(design_sample.input_path(root, label)) != digest:
            raise M2VError(f'样品来源已变化：{label}；请重新采集')
    for name, digest in value['artifacts'].items():
        if dependencies.digest(local(path.parent, name)) != digest:
            raise M2VError(f'样品产物已变化：{name}')
    design_sample.validate_source_binding(root, value)
    return value, path.parent


def validate_current_sources(root: Path, project: dict, request: dict) -> None:
    """capture 的摘要不变不代表其间接源码/资源仍当前；评审也须核验该绑定。"""
    for source in request['sources']:
        path = local(root, source).resolve()
        # 使用平台路径语义：Windows大小写别名和冗余分隔符不能绕过检查，
        # 也不把Linux上不同大小写的其他文件误判为原生采集。
        if path.parent.parent == (outputs(root) / 'samples').resolve() and path == path.parent / 'capture.json':
            identity = identifier(read(path).get('id'))
            if path.parent != (outputs(root) / 'samples' / identity).resolve():
                raise M2VError('原生采集路径与身份不符')
            load(root, project, identity)


def deliver(root: Path, project: dict, identity: str, *, blind_id: str, comparison_id: str, basis: str) -> dict:
    text(basis)
    value, directory = load(root, project, identity)
    blind, _, blind_private, blind_reuse = reuse.evidence(root, project, identifier(blind_id))
    comparison, _, comparison_private, comparison_reuse = reuse.evidence(root, project, identifier(comparison_id))
    if (blind['round'] != 'trial' or blind['reviewType'] != 'blind'
            or comparison['round'] != 'trial' or comparison['reviewType'] != 'consistency'
            or comparison.get('blindId') != blind_id
            or comparison['reviewerId'] != blind['reviewerId']):
        raise M2VError('样品交付需要同一评审者的当前trial盲看和同轮目标对照')
    if blind_reuse != comparison_reuse:
        raise M2VError('样品视觉复用须来自同一双报告收据')
    for report, private in ((blind, blind_private), (comparison, comparison_private)):
        if report['verdict'] != 'pass' or report['isolation'] != 'independent-subagent':
            raise M2VError('样品独立评审尚未通过；继续迭代，不得交付')
        request = private['request']
        if (request['fps'] != value['fps'] or request['items'] != review_items(value)
                or f'outputs/samples/{identity}/capture.json' not in request['sources']
                or value['entry'] not in request['sources']
                or not {value['width'], 393}.issubset(request['displaySizes'])
                or not request.get('references') or not request.get('conditions')):
            raise M2VError('评审未覆盖本次同源静帧、完整过程、来源或实际目标参考')
    if any(item['required'] and item['status'] != 'closed' for item in issues.load(root, required=True)):
        raise M2VError('当前周期仍有未关闭必改项；不得缩小范围或以新样品绕过')
    target = local(outputs(root), f'sample-deliveries/{identity}/delivery.json', exists=False).parent
    selection = {'version': VERSION, 'sampleId': identity, 'capture': receipt(outputs(root), directory / 'capture.json'),
                 'blindId': blind_id, 'comparisonId': comparison_id, 'basis': basis}
    if blind_reuse:
        selection['visualReuse'] = blind_reuse
    if target.exists():
        saved = read(local(target, 'delivery.json'))
        if any(saved.get(key) != val for key, val in selection.items()) or not ledger.evidence_valid_at(target, saved.get('files', [])):
            raise M2VError('已有样品交付与当前依据不符，不覆盖旧交付')
        return {'path': str(target), 'reused': True, **saved}
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.delivery-', dir=target.parent) as temporary:
        stage = Path(temporary)
        for name in [*(row['path'] for row in value['stills']), value['video']]:
            shutil.copy2(local(directory, name), stage / name)
            if dependencies.digest(stage / name) != value['artifacts'][name]:
                raise M2VError('交付复制期间样品发生变化，请重新核验')
        # CLI操作内摘要缓存不能替代发布前对外部编辑的重新读取。
        if design_sample.snapshot(root, [design_sample.input_path(root, label)
                                         for label in value['inputs']]) != value['inputs']:
            raise M2VError('交付期间样品来源发生变化，请重新采集')
        selection.update(files=[receipt(stage, path) for path in sorted(stage.iterdir())], createdAt=now())
        write(stage / 'delivery.json', selection)
        security.deliver_directory(stage, target)
    ledger.append(root, project, 'sample-delivered', data={'sampleId': identity, 'receipt': receipt(outputs(root), target / 'delivery.json')})
    logger.info('原生样品 %s 已按独立通过报告交付：%s', identity, target)
    return {'path': str(target), 'reused': False, **selection}


def server(root: Path, project: dict, identity: str, *, port: int = 0):
    from m2v.engine.http_server import LocalServer

    if type(port) is not int or not 0 <= port <= 65535:
        raise M2VError('预览端口必须为0到65535的整数')
    value, directory = load(root, project, identity)
    return LocalServer(directory / 'web', port=port, mounts={'/fonts': root / 'public/fonts'},
                       files=design_sample.media_files(root, value['config']['media']), cors=True)
