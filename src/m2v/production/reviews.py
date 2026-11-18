"""媒体隔离包和两类独立评审；无需设计合同或画面断言。"""

from __future__ import annotations

import uuid
import logging
import shutil
from datetime import datetime
from pathlib import Path

from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError
from . import ledger, dependencies, media_evidence
from .model import (
    VERSION,
    ROUNDS,
    PURPOSES,
    adoption,
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
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
logger = logging.getLogger(__name__)


def has_visual_target(request: dict) -> bool:
    return any(isinstance(path, str) and Path(path).suffix.lower() in IMAGES | VIDEO
               for path in request.get('references', []))


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
    purpose="keyframe",
):
    return dict(
        version=VERSION,
        reviewId=review_id,
        cycleId=cycle_id,
        createdAt=now(),
        round=round,
        purpose=purpose,
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
        {"version", "round", "purpose", "fps", "items", "sources", "sceneIds", "displaySizes"},
        {"reviewType", "blindId", "references", "conditions", "sampleStep", "blindReason", "film"},
    )
    if (
        request["version"] != VERSION
        or request["round"] not in ROUNDS
        or not number(request["fps"])
    ):
        raise M2VError("仅接受 version=4 的关键帧或关键样片请求")
    purpose = request["purpose"]
    review_type = request.get("reviewType", "process" if purpose == "process" else "blind")
    if purpose not in PURPOSES:
        raise M2VError("purpose 必须是 keyframe 或 process")
    if "film" in request and request["film"] is not True:
        raise M2VError("film 如有声明须为 true，表示从实际合成视频取证")
    if review_type not in ("blind", "consistency", "process"):
        raise M2VError("评审类型无效")
    if review_type == "process":
        if purpose != "process" or request.get("blindId") is not None or request.get("blindReason"):
            raise M2VError("过程直接对照不得伪造盲看身份或混用其他用途")
        if not request.get("references") or not request.get("conditions"):
            raise M2VError("过程对照必须提供实际参考和中性 conditions")
    elif purpose == "process":
        text(request.get("blindReason"))
    elif "blindReason" in request:
        raise M2VError("仅过程例外盲审可登记 blindReason")
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
    if request.get("film") and not has_visual_target(request):
        raise M2VError("正式评审须登记实际视觉参考")
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
        suffix = Path(item["path"]).suffix.lower()
        if purpose == "keyframe":
            if item["dynamic"] or (suffix not in (VIDEO if request.get("film") else IMAGES)):
                raise M2VError("关键帧只观察图片，正式关键帧须从实际合成视频取帧")
            if request.get("film") and item["window"][1] != item["window"][0] + 1:
                raise M2VError("正式关键帧的观察窗口必须恰好一帧")
        elif not item["dynamic"]:
            raise M2VError("关键样片必须覆盖视频，静帧不能替代")


def _reject_trial_sample_process(root, request):
    from .samples import is_trial_sample_process

    if is_trial_sample_process(root, request):
        raise M2VError("研究试制动态样片由总代理核验，独立评审只受理其关键帧")


def package(root: Path, manifest: dict, request: dict) -> Path:
    validate_request(request)
    _reject_trial_sample_process(root, request)
    if request["purpose"] == "process" and "reviewType" not in request:
        request = {**request, "reviewType": "process"}
    c = ledger.cycle(root)
    if c["projectId"] != manifest["id"]:
        raise M2VError("制作周期不属于当前作品")
    _, errors = ledger.history(root)
    if errors:
        raise M2VError("; ".join(errors))
    if request.get("film") and request.get("reviewType") != "consistency":
        from .film_review import pin_sources
        request = pin_sources(root, manifest, request)
    review_type = request.get("reviewType", "blind")
    blind_id = request.get("blindId")
    if review_type == "consistency":
        prior = current_report(root, manifest, identifier(blind_id))
        prior_pack, prior_binding = load_package(
            root, manifest, prior["packPath"], prior["packSha256"]
        )
        binding = ledger.binding(root, manifest, request, sealed=prior_binding["binding"])
        if (
            prior["reviewType"] != "blind"
            or prior["round"] != request["round"]
            or prior_binding["request"]["purpose"] != request["purpose"]
            or prior_binding["request"].get("blindReason") != request.get("blindReason")
            or any(prior_binding["request"].get(key) != request.get(key)
                   for key in ("fps", "displaySizes", "sampleStep"))
            or prior_binding["binding"] != binding
            or prior_binding["request"]["items"] != request["items"]
        ):
            raise M2VError("对照必须复用同轮盲看的相同媒体、来源和观察范围")
        if not request.get("references") and not request.get("conditions"):
            raise M2VError("对照包缺少目标媒体或中性原条件")
    elif blind_id is not None:
        raise M2VError("盲看不能引用旧报告")
    else:
        binding = ledger.binding(root, manifest, request)
    base = outputs(root)
    rid = uuid.uuid4().hex
    target = local(base, f"review-pack/{rid}/manifest.json", exists=False).parent
    target.mkdir(parents=True)
    items, files = [], []
    if review_type == 'consistency':
        prior_directory = local(base, prior['packPath']).parent
        items = prior_pack['items']
        # 同轮输入完全相同，复用已核验净化媒体；独立复制防止一包修改污染另一包。
        for record in prior_pack['files']:
            if record['path'] == 'questions.md':
                continue
            source = local(prior_directory, record['path'])
            destination = local(target, record['path'], exists=False)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if digest(destination) != record['sha256']:
                raise M2VError('同轮观察媒体复制期间摘要发生变化')
    for index, item in enumerate([] if review_type == 'consistency' else request["items"]):
        source = local(base, item["path"])
        if source.suffix.lower() not in MEDIA:
            raise M2VError("评审包只接受媒体，不接受源码或设计文档")
        name = f"evidence-{index:04d}"
        path = target / (name + (source.suffix.lower() if item["dynamic"] else ".png"))
        start, end = item["window"]
        if item["dynamic"]:
            fps = request["fps"]
            if not request.get("film"):
                source_duration = media_evidence.duration(source)
                if source_duration <= 0 or source_duration + 1 / fps < end / fps:
                    raise M2VError("视频不能覆盖完整观察窗口")
            ffmpeg(
                [
                    "-i", str(source),
                    "-vf", f"trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS",
                    "-af", f"atrim=start={start / fps}:end={end / fps},asetpts=PTS-STARTPTS",
                    "-t", str((end - start) / fps),
                    "-map_metadata", "-1", "-map_chapters", "-1",
                    "-r", str(fps), "-c:v", "libx264", "-c:a", "aac",
                    str(path),
                ]
            )
            clip_duration = media_evidence.duration(path)
            if (
                clip_duration <= 0
                or clip_duration + 1 / request["fps"] < (end - start) / request["fps"]
            ):
                raise M2VError("生成的过程片段覆盖不足")
            step = request.get("sampleStep", 1)
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
            seek = ["-vf", f"select=eq(n\\,{start})"] if request.get("film") else []
            ffmpeg(["-i", str(source), *seek, "-map_metadata", "-1",
                    "-frames:v", "1", str(path)])
            derived = {w: target / f"{name}-{w}.png" for w in request["displaySizes"]}
            derive_images(path, derived)
            sequence = [{"frame": start, "path": path.name,
                         "displayPaths": [p.name for p in derived.values()]}]
        items.append(
            {
                "id": item["id"],
                "path": path.name,
                "window": item["window"],
                "dynamic": item["dynamic"],
                "sequence": sequence,
                **({"filmWindow": binding["film"][item["id"]]["window"]} if request.get("film") else {}),
            }
        )
    if review_type in ("consistency", "process"):
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
        "记录查看窗口、显示尺寸、帧序列/声音信号覆盖与限制。不能确认则 insufficient。"
        "dynamic标识视频媒体，不自动承诺运动；静止编码只判断静态表现与一致性，"
        "未提供的运动、停留时间、声音或全片保持未验证，不把局部静态通过扩成动态基线。"
        "分别观察 understanding、presentation、representativeness；表现须具体观察构图、主体、排版及适用材质光影，"
        "代表性判断当前所给局部的实际形象与完整过程是否充分、是否占位。"
        "不能仅凭清楚可读或无技术错误判定视觉品质。作者解释不能补足实际效果。\n"
        "按完整画面区分抽象意象与精确信息职责：形体、空间或动作可与清晰文字/读数协作，"
        "抽象主体不默认承担逐层字形读取或逐物具象辨认。整体形象与表达成立、必要信息清楚时，"
        "局部辨认代价作为打磨限制，不仅因此fail；关键误导、唯一读数不可读、核心形象失效仍须阻断。"
        "未知意图记录疑问供对照核原条件，不臆定更高要求，也不因抽象标签自动通过。\n"
    )
    if review_type == 'blind':
        questions += "盲看不能仅因隔离未见目标而自动insufficient；目标兑现由同轮对照另验。\n"
    if review_type in ("consistency", "process"):
        questions += (
            "先核对 conditions 中相关原始要求、媒体对应关系及适用范围，与作者转化是否一致；"
            "作者自写例外不能授权缩小原要求。原始依据缺失则对应目标未验证，"
            "发现整体风格被限为单场或另一套核心视觉载体时，不按放宽条件确认通过。"
            "构图可随内容变化；同色同字体不等于整体形体、材质、空间、光影及适用运动一致。"
            "选中、赞许或历史通过不提示本轮应通过。\n"
        )
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
    from .review_tasks import guidance
    (target / "questions.md").write_text(guidance(request["purpose"]) + questions, encoding="utf-8")
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
        purpose=request["purpose"],
        blind_id=blind_id,
        requires_comparison=review_type != "process" and bool(
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
    from .review_tasks import create_task
    create_task(root, target)
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
        film = private["binding"].get("film", {})
        if film and not ledger.evidence_valid(root, [item["provenance"] for item in film.values()]):
            raise M2VError("历史合成视频旁车摘要失配")
    elif private["binding"] != ledger.binding(root, manifest, private["request"], sealed=private["binding"]):
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


def still_current_film_items(root, manifest, report_id):
    """为状态保留同一批次里未受影响的窗口，闭环和报告采用仍校验完整包。"""
    from . import film_review, reuse, samples

    if reuse.has_record(root, report_id):
        return None
    report = sealed_report(root, manifest, report_id, historical=True)
    if (report["verdict"] != "pass" or report["isolation"] != "independent-subagent"
            or not report["hasVisualTarget"]):
        return None
    _, private = historical_package(root, manifest, report["packPath"], report["packSha256"])
    binding = private["binding"]
    request = private["request"]
    film = binding.get("film")
    if not film or ledger.sources(root, request) != binding["sources"]:
        return None
    samples.validate_current_sources(root, manifest, request)
    retained = {}
    for item, media in zip(request["items"], binding["media"], strict=True):
        try:
            current = film_review.composition_binding(
                root, manifest, {**request, "items": [item]}, [media], sealed=binding)
            if current[item["id"]] == film[item["id"]]:
                retained.update(current)
        except (M2VError, OSError, ValueError, KeyError, TypeError):
            continue
    return (report, retained, binding["conditions"]) if retained else None


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
            "adoption",
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
    if report["reviewType"] != "consistency" and "blindId" in report:
        raise M2VError("仅同轮 consistency 对照可以引用 blindId")
    if report["adoption"] != adoption(report["verdict"]):
        raise M2VError("采用结论必须明确：仅 pass 可 adopt，fail/insufficient 必须 reject")
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
            "purpose": current["purpose"],
            "adoption": current["adoption"],
        }
    _reject_trial_sample_process(root, private["request"])
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
        [report.get("blindId")] if report["reviewType"] == "consistency" else []
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
    if report["focus"] != "comprehensive":
        raise M2VError("当前独立评审使用综合职责")
    if not isinstance(report["coverage"], list):
        raise M2VError("coverage 必须为列表")
    by_id = {item["id"]: item for item in pack["items"]}
    seen = set()
    for item in report["coverage"]:
        fields(
            item,
            {"id", "window", "status", "adoption", "observations", "limitations", "assessment"},
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
        if item["adoption"] != adoption(item["status"]):
            raise M2VError("每个观察项必须给出与状态一致的明确采用结论")
    states = [x["status"] for x in report["coverage"]]
    expected = "fail" if "fail" in states else "insufficient" if "insufficient" in states else "pass"
    if seen != set(by_id) or report["verdict"] != expected:
        raise M2VError("报告覆盖不足或失败结论无对应观察")
    rid = report_digest
    report.update(
        id=rid,
        cycleId=ledger.cycle(root)["cycleId"],
        requiresComparison=pack["requiresComparison"],
        purpose=pack["purpose"],
        hasVisualTarget=has_visual_target(private["request"]),
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
    return {"id": rid, "round": report["round"], "purpose": pack["purpose"],
            "verdict": report["verdict"], "adoption": report["adoption"]}


def compare(root: Path, project: dict, blind_id: str) -> Path:
    """只派生封存请求，不接受作者在盲看后更换目标。"""
    report = current_report(root, project, identifier(blind_id))
    if report["reviewType"] != "blind":
        raise M2VError("compare 需要当前盲报告 ID")
    _, private = load_package(root, project, report["packPath"], report["packSha256"])
    return package(root, project, {**private["request"], "reviewType": "consistency", "blindId": blind_id})


def package_result(root: Path, package: Path) -> dict:
    """将实际包与已生成任务一起返回，调用方无需拼接内部路径。"""
    task = ledger.directory(root) / 'review-tasks' / package.name
    return {'path': str(package), 'task': str(task / 'task.md'),
            'reportTemplate': str(task / 'report-template.json'),
            'invocationTemplate': str(task / 'invocation-template.json')}
