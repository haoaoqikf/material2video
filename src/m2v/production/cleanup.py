"""在作品写锁内保留当前周期的评审媒体和问题证据，再调用通用输出清理。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.output_cleanup import cleanup_after_render
from . import issues, ledger
from .model import VERSION, fields
from .storage import local, locked, read


def retained_media(root: Path) -> set[Path]:
    """包内净化副本不能替代源媒体：来源绑定仍核验源文件摘要。"""
    base = outputs(root)
    if not (base / "production/workflow.json").exists():
        return set()
    events, errors = ledger.history(root)
    if errors:
        raise M2VError("; ".join(errors))
    protected: set[Path] = set()
    for issue in issues.load(root, check_closures=False):
        evidence = issue.get("evidence", [])
        if not isinstance(evidence, list):
            raise M2VError("问题证据引用无效")
        for entry in evidence:
            fields(entry, {"path", "sha256"})
            protected.add(local(base, entry["path"], exists=False))
    captures = {
        'outputs/' + event['data']['receipt']['path']: event['data']['receipt']
        for event in events if event['type'] == 'sample-captured'
    }
    for event in events:
        if event["type"] != "package":
            continue
        sealed = event["data"]["receipt"]
        if not ledger.evidence_valid(root, [sealed]):
            raise M2VError("评审源媒体引用记录损坏，未执行清理")
        private = read(local(base, sealed["path"]))
        fields(private, {"version", "request", "binding", "manifest"})
        if private["version"] != VERSION:
            raise M2VError("评审源媒体引用版本未知，未执行清理")
        binding = private["binding"]
        fields(binding, {"conditions", "sources", "media", "references"}, {"film"})
        for observation in binding.get("film", {}).values():
            sidecar = observation["provenance"]
            if not ledger.evidence_valid(root, [sidecar]):
                raise M2VError("正式评审旁车摘要失配，未执行清理")
            protected.add(local(base, sidecar["path"]))
        for key in ("media", "references"):
            if not isinstance(binding[key], list):
                raise M2VError("评审源媒体引用无效，未执行清理")
            for entry in binding[key]:
                fields(entry, {"path", "sha256"})
                # 已失效/未导入的包也保留其明确引用，不把内容过期误作可删除。
                protected.add(local(base, entry["path"], exists=False))
        for source in set(private['request']['sources']) & captures.keys():
            capture = captures.pop(source)
            if not ledger.evidence_valid(root, [capture]):
                raise M2VError("评审引用的原生采集记录损坏，未执行清理")
            capture_path = local(base, capture['path'])
            # 当前来源校验逐个检查原生采集产物，未入评审窗口的静帧也参与有效性。
            artifacts = read(capture_path)['artifacts']
            if not isinstance(artifacts, dict):
                raise M2VError("原生采集产物登记无效，未执行清理")
            protected.update(local(capture_path.parent, name, exists=False) for name in artifacts)
    return protected


def cleanup_render_outputs(root: Path, current_video: Path) -> list[str]:
    """清理失败只报告，不影响已生成候选；与 pack/import 共用锁避免引用竞态。"""
    try:
        with locked(root), ledger.query():
            protected = retained_media(root)
            return cleanup_after_render(
                outputs(root), current_video,
                preserve_visual_evidence=True, protected_files=protected,
            )
    except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
        return [f"无法确认评审媒体或问题证据引用，未执行清理：{exc}"]
