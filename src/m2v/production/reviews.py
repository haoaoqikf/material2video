"""媒体隔离包和两类独立评审；无需设计合同或画面断言。"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import ledger, dependencies, media_evidence
from .model import (
    VERSION,
    ROUNDS,
    fields,
    identifier,
    text,
    window,
    number,
    ffmpeg,
    now,
)
from .storage import local, read, receipt, write
from .evidence_images import derive_images

MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".wav", ".mp3"}
VIDEO = {".mp4", ".webm"}
logger = logging.getLogger(__name__)


def build_manifest(
    *,
    review_id,
    cycle_id,
    round,
    fps,
    items,
    files,
    display_sizes,
    review_type="blind",
    blind_id=None,
    requires_comparison=False,
):
    return dict(
        version=VERSION,
        reviewId=review_id,
        cycleId=cycle_id,
        createdAt=now(),
        round=round,
        fps=fps,
        items=items,
        files=files,
        displaySizes=display_sizes,
        reviewType=review_type,
        blindId=blind_id,
        requiresComparison=requires_comparison,
    )


def validate_request(request):
    fields(
        request,
        {"version", "round", "fps", "items", "sources", "sceneIds", "displaySizes"},
        {"reviewType", "blindId", "references", "conditions", "sampleStep"},
    )
    if (
        request["version"] != VERSION
        or request["round"] not in ROUNDS
        or not number(request["fps"])
    ):
        raise M2VError("仅接受 version=2 的 trial/final 媒体评审请求")
    if request.get("reviewType", "blind") not in ("blind", "consistency"):
        raise M2VError("评审类型无效")
    if not isinstance(request["items"], list) or not request["items"]:
        raise M2VError("评审必须包含实际媒体")
    if (
        not isinstance(request["displaySizes"], list)
        or not request["displaySizes"]
        or any(type(w) is not int or w < 1 for w in request["displaySizes"])
        or 393 not in request["displaySizes"]
    ):
        raise M2VError("显示尺寸必须包含 393 宽手机图")
    if (
        type(request.get("sampleStep", 1)) is not int
        or request.get("sampleStep", 1) < 1
    ):
        raise M2VError("sampleStep 必须为正整数")
    if not isinstance(request.get("references", []), list):
        raise M2VError("references 必须为路径列表")
    if not isinstance(request.get("conditions", []), list):
        raise M2VError("conditions 必须为中性条件列表")
    for condition in request.get("conditions", []):
        text(condition)
    # 只验证已声明目标的配套输入；研究深度与效果兑现仍须实际观察。
    if request.get("references") and not request.get("conditions"):
        raise M2VError("references 目标媒体必须配套非空 conditions，说明中性可观察采用特征")
    seen = set()
    for item in request["items"]:
        fields(item, {"id", "path", "window", "dynamic"})
        identifier(item["id"])
        window(item["window"])
        if (
            item["id"] in seen
            or type(item["dynamic"]) is not bool
            or not isinstance(item["path"], str)
        ):
            raise M2VError("媒体 ID 重复、路径或 dynamic 类型无效")
        seen.add(item["id"])
        if item["dynamic"] and Path(item["path"]).suffix.lower() not in VIDEO:
            raise M2VError("动态观察需要视频，静帧不能代替")


def package(root: Path, manifest: dict, request: dict) -> Path:
    validate_request(request)
    c = ledger.cycle(root)
    if c["projectId"] != manifest["id"]:
        raise M2VError("制作周期不属于当前作品")
    _, errors = ledger.history(root)
    if errors:
        raise M2VError("; ".join(errors))
    binding = ledger.binding(root, manifest, request)
    review_type = request.get("reviewType", "blind")
    blind_id = request.get("blindId")
    if review_type == "consistency":
        prior = current_report(root, manifest, identifier(blind_id))
        prior_pack, prior_binding = load_package(
            root, manifest, prior["packPath"], prior["packSha256"]
        )
        if (
            prior["reviewType"] != "blind"
            or prior["round"] != request["round"]
            or prior_binding["binding"] != binding
            or prior_binding["request"]["items"] != request["items"]
        ):
            raise M2VError("对照必须复用同轮盲看的相同媒体、来源和观察范围")
        if not request.get("references") and not request.get("conditions"):
            raise M2VError("对照包缺少目标媒体或中性原条件")
    elif blind_id is not None:
        raise M2VError("盲看不能引用旧报告")
    if request["round"] == "final":
        final = binding["final"]
        if (
            len(request["items"]) != 1
            or request["items"][0]["window"] != [0, final["durationFrames"]]
            or request["fps"] != final["fps"]
            or binding["media"][0]["sha256"] != final["candidateSha256"]
            or not request["items"][0]["dynamic"]
        ):
            raise M2VError("终审必须覆盖当前完整候选的全片窗口与实际帧率")
    base = outputs(root)
    rid = uuid.uuid4().hex
    target = base / "review-pack" / rid
    target.mkdir(parents=True)
    items, files = [], []
    for index, item in enumerate(request["items"]):
        source = local(base, item["path"])
        if source.suffix.lower() not in MEDIA:
            raise M2VError("评审包只接受媒体，不接受源码或设计文档")
        name = f"evidence-{index:04d}"
        path = target / (name + source.suffix.lower())
        start, end = item["window"]
        if source.suffix.lower() in VIDEO:
            source_duration = media_evidence.duration(source)
            if (
                source_duration <= 0
                or source_duration + 1 / request["fps"] < end / request["fps"]
            ):
                raise M2VError("视频不能覆盖完整观察窗口")
            if request["round"] == "final":
                # 当前完整候选只净化封装元数据，不再次编码全片。
                ffmpeg(
                    [
                        "-i",
                        str(source),
                        "-map_metadata",
                        "-1",
                        "-map_chapters",
                        "-1",
                        "-c",
                        "copy",
                        str(path),
                    ]
                )
            else:
                ffmpeg(
                    [
                        "-i",
                        str(source),
                        "-ss",
                        str(start / request["fps"]),
                        "-t",
                        str((end - start) / request["fps"]),
                        "-map_metadata",
                        "-1",
                        "-map_chapters",
                        "-1",
                        "-r",
                        str(request["fps"]),
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        str(path),
                    ]
                )
            clip_duration = media_evidence.duration(path)
            if (
                clip_duration <= 0
                or clip_duration + 1 / request["fps"] < (end - start) / request["fps"]
            ):
                raise M2VError("生成的过程片段覆盖不足")
            step = request.get(
                "sampleStep",
                max(1, round(request["fps"] / 2)) if request["round"] == "final" else 1,
            )
            frames = sorted(set(range(0, end - start, step)) | {end - start - 1})
            frame_dir = target / name
            frame_dir.mkdir()
            # 单次解码提取有序帧；不逐帧启动媒体子进程。
            selection = f"not(mod(n,{step}))+eq(n,{end - start - 1})"
            ffmpeg(
                [
                    "-i",
                    str(path),
                    "-vf",
                    f"select='{selection}'",
                    "-vsync",
                    "0",
                    str(frame_dir / "%06d.png"),
                ]
            )
            extracted = sorted(frame_dir.glob("*.png"))
            if len(extracted) != len(frames):
                raise M2VError("有序帧未完整提取，请核对实际帧率与窗口")
            sequence = []
            for frame, image in zip(frames, extracted):
                derived = {
                    w: image.with_name(f"{image.stem}-{w}.png")
                    for w in request["displaySizes"]
                }
                derive_images(image, derived)
                sequence.append(
                    {
                        "frame": start + frame,
                        "path": image.relative_to(target).as_posix(),
                        "displayPaths": [
                            p.relative_to(target).as_posix() for p in derived.values()
                        ],
                    }
                )
        else:
            ffmpeg(
                [
                    "-i",
                    str(source),
                    "-map_metadata",
                    "-1",
                    *(
                        ["-frames:v", "1"]
                        if source.suffix.lower() not in {".wav", ".mp3"}
                        else []
                    ),
                    str(path),
                ]
            )
            sequence = []
            if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                derived = {
                    w: target / f"{name}-{w}.png" for w in request["displaySizes"]
                }
                derive_images(path, derived)
                sequence = [
                    {
                        "frame": start,
                        "path": path.name,
                        "displayPaths": [p.name for p in derived.values()],
                    }
                ]
        items.append(
            {
                "id": item["id"],
                "path": path.name,
                "window": item["window"],
                "dynamic": item["dynamic"],
                "sequence": sequence,
            }
        )
    if review_type == "consistency":
        write(target / "conditions.json", request.get("conditions", []))
        for index, reference in enumerate(request.get("references", [])):
            source = local(base, reference)
            if source.suffix.lower() not in MEDIA:
                raise M2VError("目标只能为媒体")
            ffmpeg(
                [
                    "-i",
                    str(source),
                    "-map_metadata",
                    "-1",
                    str(target / f"target-{index:04d}{source.suffix.lower()}"),
                ]
            )
    questions = (
        "只读取本包。先保存实际看见的对象、变化、理解、视觉表现和疑问；"
        "记录查看窗口、显示尺寸、播放/帧序列/声音覆盖与限制。不能确认则 insufficient。"
        "dynamic标识视频媒体，不自动承诺运动；静止编码只判断静态表现与一致性，"
        "未提供的运动、停留时间、声音或全片保持未验证，不把局部静态通过扩成动态基线。"
        "分别观察 understanding、presentation、representativeness；表现须具体观察构图、主体、排版及适用材质光影，"
        "不能仅凭清楚可读或无技术错误判定视觉品质。作者解释不能补足实际效果。\n"
    )
    if review_type == "consistency":
        questions += (
            "按 conditions 区分整体品质标杆、专项目标与备选/历史比较媒体的用途；"
            "对照实际目标的整体效果及采用特征，记录兑现情况、主要差距、收益/损失及证据限制。"
            "局部特征齐全不等于整体品质成立，相对备选或旧版更好也不等于达到目标；"
            "不能用理解通过替代视觉表现或代表性。\n"
            if request.get("references") else
            "本包仅核对中性条件，没有目标媒体；不得据此验证未提供的风格目标。\n"
        )
    if request["round"] == "trial":
        questions += (
            "在 observations 中说明具体吸引力、普通之处及当前最大差距；"
            "区分值得继续打磨与足以作为后续标准的依据，允许全部不值得继续，不强制选赢家。"
            "候选排名或本范围 pass 不能自动授权展开全片；未覆盖的目标与制作链路保持未验证。"
            "所有 items 仍须如实覆盖，淘汰不免除已导入失败的复查要求。\n"
        )
    (target / "questions.md").write_text(questions, encoding="utf-8")
    files = [receipt(target, p) for p in sorted(target.rglob("*")) if p.is_file()]
    pack = build_manifest(
        review_id=rid,
        cycle_id=c["cycleId"],
        round=request["round"],
        fps=request["fps"],
        items=items,
        files=files,
        display_sizes=request["displaySizes"],
        review_type=review_type,
        blind_id=blind_id,
        requires_comparison=bool(
            request.get("references") or request.get("conditions")
        ),
    )
    write(target / "manifest.json", pack)
    private_path = ledger.directory(root) / "packages" / f"{rid}.json"
    write(
        private_path,
        {
            "version": VERSION,
            "request": request,
            "binding": binding,
            "manifest": receipt(base, target / "manifest.json"),
        },
    )
    ledger.append(
        root,
        manifest,
        "package",
        data={"reviewId": rid, "receipt": receipt(base, private_path)},
    )
    logger.info(
        "生成 %s 隔离评审包 %s，覆盖 %d 个窗口", request["round"], rid, len(items)
    )
    return target


def load_package(root, manifest, pack_path, pack_sha256):
    return ledger.query_value(
        ("package", root, pack_path, pack_sha256),
        lambda: _load_package(root, manifest, pack_path, pack_sha256),
    )


def historical_package(root, manifest, pack_path, pack_sha256):
    """只读观察身份，不能直接授权当前作品；与当前技术验证分开缓存。"""
    return ledger.query_value(
        ('historical-package', root, pack_path, pack_sha256),
        lambda: _load_package(root, manifest, pack_path, pack_sha256, historical=True),
    )


def _load_package(root, manifest, pack_path, pack_sha256, *, historical=False):
    path = local(outputs(root), pack_path)
    if (
        path.name != "manifest.json"
        or path.parent.parent != outputs(root) / "review-pack"
    ):
        raise M2VError("评审包路径无效")
    if dependencies.digest(path) != pack_sha256:
        raise M2VError("评审包摘要变化")
    pack = read(path)
    if (
        pack.get("version") != VERSION
        or pack.get("cycleId") != ledger.cycle(root)["cycleId"]
    ):
        raise M2VError("旧评审包或旧周期不能授权当前作品")
    events, errors = ledger.history(root)
    sealed = next(
        (
            e["data"]["receipt"]
            for e in events
            if e["type"] == "package" and e["data"]["reviewId"] == pack["reviewId"]
        ),
        None,
    )
    if errors or not sealed or not ledger.evidence_valid(root, [sealed]):
        raise M2VError("私有来源绑定记录损坏")
    private = read(local(outputs(root), sealed["path"]))
    if private["manifest"] != receipt(
        outputs(root), path
    ) or not ledger.evidence_valid_at(path.parent, pack["files"]):
        raise M2VError("包内证据摘要失配")
    if historical:
        # 仅显式视觉复用可忽略旧源码与当前源码的差异。封存请求、原摘要、
        # 包内媒体以及完整源媒体/参考仍须完整，不能跳过整个旧绑定。
        if not all(ledger.evidence_valid(root, private['binding'][key])
                   for key in ('media', 'references') if private['binding'][key]):
            raise M2VError('历史源媒体或参考摘要失配')
    elif private["binding"] != ledger.binding(root, manifest, private["request"]):
        raise M2VError("来源、媒体或当前候选已变化，评审包过期")
    else:
        from .samples import validate_current_sources
        validate_current_sources(root, manifest, private['request'])
    return pack, private


def current_report(root, manifest, report_id):
    return ledger.query_value(
        ("report", root, report_id), lambda: _current_report(root, manifest, report_id)
    )


def _current_report(root, manifest, report_id):
    from . import reuse
    if reuse.has_record(root, report_id):
        return reuse.resolve(root, manifest, report_id)[0]
    return sealed_report(root, manifest, report_id)


def sealed_report(root, manifest, report_id, *, historical=False):
    """核验真实封存身份；historical 不授权当前技术，只用于显式 trial 复用。"""
    identifier(report_id)
    events, errors = ledger.history(root)
    event = next(
        (
            e
            for e in events
            if e["type"] == "review" and e["data"]["reportId"] == report_id
        ),
        None,
    )
    if (
        errors
        or event is None
        or not ledger.evidence_valid(root, event["data"]["receipts"])
    ):
        raise M2VError("评审记录损坏、缺失或摘要失配")
    report = read(local(outputs(root), event["data"]["reportPath"]))
    if historical:
        historical_package(root, manifest, report['packPath'], report['packSha256'])
    else:
        load_package(root, manifest, report["packPath"], report["packSha256"])
    if not ledger.evidence_valid(root, [report["invocation"]]):
        raise M2VError("独立调用记录已变化")
    return report


def import_report(root, manifest, path):
    from . import issues

    report_digest = dependencies.digest(path)
    report = read(path)
    fields(
        report,
        {
            "version",
            "round",
            "reviewType",
            "packPath",
            "packSha256",
            "reviewerId",
            "isolation",
            "focus",
            "verdict",
            "observations",
            "coverage",
            "invocation",
        },
        {"blindId"},
    )
    if (
        report["version"] != VERSION
        or report["round"] not in ROUNDS
        or report["verdict"] not in ("pass", "fail", "insufficient")
        or report["isolation"]
        not in ("independent-subagent", "self-review", "external-review")
    ):
        raise M2VError("旧报告、结论或隔离类型无效")
    identifier(report["reviewerId"])
    text(report["observations"])
    pack, private = load_package(
        root, manifest, report["packPath"], report["packSha256"]
    )
    events, _ = ledger.history(root)
    if any(
        e["type"] == "review" and e["data"]["reportId"] == report_digest for e in events
    ):
        current = current_report(root, manifest, report_digest)
        if current["verdict"] == "fail":
            issues.from_review(root, current)
        return {
            "id": report_digest,
            "round": current["round"],
            "verdict": current["verdict"],
        }
    issues.load(root, required=True)
    if any(report[k] != pack[k] for k in ("round", "reviewType")):
        raise M2VError("报告轮次或类型与包不一致")
    if not ledger.evidence_valid(root, [report["invocation"]]):
        raise M2VError("独立调用记录无效")
    invocation = read(local(outputs(root), report["invocation"]["path"]))
    fields(
        invocation,
        {
            "id",
            "reviewerId",
            "freshContext",
            "startedAt",
            "completedAt",
            "inputPaths",
            "readReportIds",
        },
    )
    if invocation["reviewerId"] != report["reviewerId"] or (
        report["isolation"] == "independent-subagent"
        and invocation["freshContext"] is not True
    ):
        raise M2VError("独立调用身份或新上下文无效")
    try:
        created, start, end = [
            datetime.fromisoformat(t.replace("Z", "+00:00"))
            for t in (
                pack["createdAt"],
                invocation["startedAt"],
                invocation["completedAt"],
            )
        ]
        if (
            not all(t.tzinfo for t in (created, start, end))
            or not created <= start <= end
        ):
            raise ValueError("时间顺序无效")
    except (ValueError, TypeError, AttributeError) as exc:
        raise M2VError("调用时间必须有时区且晚于包创建") from exc
    pack_dir = local(outputs(root), report["packPath"]).parent
    allowed = {entry["path"] for entry in pack["files"]} | {"manifest.json"}
    if (
        not isinstance(invocation["inputPaths"], list)
        or not invocation["inputPaths"]
        or any(
            not local(outputs(root), p).is_relative_to(pack_dir)
            or local(outputs(root), p).relative_to(pack_dir).as_posix() not in allowed
            for p in invocation["inputPaths"]
        )
    ):
        raise M2VError("独立调用只能读取包内登记文件")
    if invocation["readReportIds"] != (
        [] if report["reviewType"] == "blind" else [report.get("blindId")]
    ):
        raise M2VError("盲看不能读取旧报告；对照只能读取自身同轮盲看")
    if report["reviewType"] == "consistency":
        prior = current_report(root, manifest, identifier(report.get("blindId")))
        if (
            pack["blindId"] != report["blindId"]
            or prior["reviewerId"] != report["reviewerId"]
            or prior["round"] != report["round"]
            or prior["focus"] != report["focus"]
            or prior["isolation"] != report["isolation"]
        ):
            raise M2VError("对照须来自同一评审者的同轮盲看")
    expected_focus = (
        ledger.cycle(root)["finalFocuses"]
        if report["round"] == "final"
        else ["comprehensive"]
    )
    if report["focus"] not in expected_focus:
        raise M2VError("评审职责与周期要求不一致")
    if report["round"] == "final":
        events, _ = ledger.history(root)
        if any(
            e["type"] == "review"
            and e["data"]["round"] == "final"
            and e["data"]["reviewerId"] == report["reviewerId"]
            and e["data"]["focus"] != report["focus"]
            for e in events
        ):
            raise M2VError("分工终审必须由互相隔离的不同评审者执行")
        # 跨当前作品各个新周期检查，重置周期不会让旧试制者重新获得终审资格。
        for prior_path in (outputs(root) / "production").glob("*/reports/*.json"):
            prior = read(
                local(outputs(root), prior_path.relative_to(outputs(root)).as_posix())
            )
            if (
                prior.get("round") == "trial"
                and prior.get("reviewerId") == report["reviewerId"]
            ):
                raise M2VError("终审必须使用未参与前期试制的新评审者")
    if not isinstance(report["coverage"], list):
        raise M2VError("coverage 必须为列表")
    by_id = {item["id"]: item for item in pack["items"]}
    seen = set()
    for item in report["coverage"]:
        fields(
            item,
            {"id", "window", "status", "observations", "limitations", "assessment"},
        )
        if (
            item["id"] in seen
            or item["id"] not in by_id
            or item["window"] != by_id[item["id"]]["window"]
        ):
            raise M2VError("报告必须覆盖包内完整窗口，且不得重复")
        seen.add(item["id"])
        text(item["observations"])
        if not isinstance(item["limitations"], list) or any(
            not isinstance(x, str) for x in item["limitations"]
        ):
            raise M2VError("必须如实记录覆盖限制")
        fields(
            item["assessment"], {"understanding", "presentation", "representativeness"}
        )
        states = []
        for value in item["assessment"].values():
            fields(value, {"status", "observations"})
            if value["status"] not in ("pass", "fail", "insufficient"):
                raise M2VError("观察判断状态无效")
            text(value["observations"])
            states.append(value["status"])
        expected = (
            "fail"
            if "fail" in states
            else "insufficient"
            if "insufficient" in states
            else "pass"
        )
        if item["status"] != expected or (
            report["verdict"] == "pass" and item["status"] != "pass"
        ):
            raise M2VError("不能把理解、表现或代表性不足合并成通过")
    if seen != set(by_id) or (
        report["verdict"] == "fail"
        and not any(x["status"] == "fail" for x in report["coverage"])
    ):
        raise M2VError("报告覆盖不足或失败结论无对应观察")
    rid = report_digest
    report.update(
        id=rid,
        cycleId=ledger.cycle(root)["cycleId"],
        requiresComparison=pack["requiresComparison"],
    )
    target = ledger.directory(root) / "reports" / f"{rid}.json"
    write(target, report)
    data = {k: report[k] for k in ("round", "focus", "reviewerId")}
    data.update(
        reportId=rid,
        reportPath=target.relative_to(outputs(root)).as_posix(),
        receipts=[receipt(outputs(root), target), report["invocation"]],
    )
    ledger.append(root, manifest, "review", data=data)
    if report["verdict"] == "fail":
        issues.from_review(root, report)
    logger.info(
        "导入 %s 评审 %s：%s（%s）",
        report["round"],
        rid,
        report["verdict"],
        report["isolation"],
    )
    return {"id": rid, "round": report["round"], "verdict": report["verdict"]}
