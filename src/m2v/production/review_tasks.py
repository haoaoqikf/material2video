"""自动派生评审机械材料；不生成观察、真实调用或通过资格。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.delivery import outputs
from . import ledger
from .model import VERSION
from .storage import local, read, receipt, write


def guidance(purpose: str) -> str:
    shared = (
        "每项和整体必须明确通过或不通过：仅pass可adopt，fail/insufficient必须reject。"
        "不足须指出缺少什么证据；不使用基本达到、有潜力、大体可以等话代替采用结论。"
        "失败说明具体位置/帧窗、显示条件、现象、违反目标和阻断影响；"
        "通过说明已达到的具体表现，次要建议不得掩盖核心失败。不用总分、排名或投票抵消失败。\n"
    )
    if purpose == "process":
        return shared + (
            "本轮是过程验证：先记录实际可辨认的变化与因果，再核对中性目标和实际参考。"
            "检查完整动作、身份连续、节奏、衔接、声画配合及运动中的材质空间稳定性。"
            "有字幕时核对与口播同步、停留、换句节奏、切镜及运动中的遮挡和深浅对比；说明证据覆盖。"
            "作者解释不能补足实际过程；不重新以个人风格偏好推翻已成立方向。\n"
        )
    return shared + (
        "以所选风格的世界级设计和制作完成度严格判断：创意表达、整体形象、构图注意力、"
        "排版色彩、实现细节、风格一致性及适用实际标杆差距。"
        "有字幕时观察合成画面中的字号、断行、层级、安全区、明暗对比及手机尺寸可读性。苹果只说明品质高度，"
        "不是固定风格，不要求所有作品有极简留白、写实材质或品牌字形。"
        "手绘、纪实、拼贴、抽象、极繁等按其表达机制判断，但风格标签不能免责粗糙或缺陷。"
        "仅可读、无遮挡、技术正常、组件齐全、候选最好都不足以证明世界级美术表现。"
        "盲看先判断作品自身，实际标杆和原要求只在同轮对照中读取；"
        "不因盲包未提供参考而自动否定当前画面的代表性。\n"
    )


def create_task(root: Path, package: Path) -> Path:
    """模板留在隔离包外，避免把未完成记录混入不可变观察证据。"""
    pack = read(package / "manifest.json")
    relative = f"production/{ledger.cycle(root)['cycleId']}/review-tasks/{pack['reviewId']}"
    target = local(outputs(root), relative + '/report-template.json', exists=False).parent
    report = {
        "version": VERSION, "round": pack["round"], "reviewType": pack["reviewType"],
        "packPath": (package / "manifest.json").relative_to(outputs(root)).as_posix(),
        "packSha256": receipt(outputs(root), package / "manifest.json")["sha256"],
        "reviewerId": "", "isolation": "independent-subagent", "focus": "comprehensive",
        "verdict": "insufficient", "adoption": "reject", "observations": "",
        "coverage": [{"id": item["id"], "window": item["window"],
                      "status": "insufficient", "adoption": "reject", "observations": "",
                      "limitations": [], "assessment": {
                          key: {"status": "insufficient", "observations": ""}
                          for key in ("understanding", "presentation", "representativeness")}}
                     for item in pack["items"]],
        "invocation": {"path": "", "sha256": ""},
    }
    if pack["reviewType"] == "consistency":
        report["blindId"] = pack["blindId"]
    write(target / "report-template.json", report)
    write(target / "invocation-template.json", {
        "id": "", "reviewerId": "", "freshContext": True,
        "startedAt": "", "completedAt": "", "inputPaths": [],
        "readReportIds": [pack["blindId"]] if pack["reviewType"] == "consistency" else [],
    })
    (target / "task.md").write_text(
        f"# 独立评审任务\n\n用途：{pack['purpose']}；类型：{pack['reviewType']}。\n\n"
        f"只读包：{report['packPath']}。只读取清单登记证据和 questions.md；"
        "不得读取作者源码、设计理由、研究报告或其他轮次结论。"
        "同轮对照仅可读取本评审者自身绑定盲报告。\n\n"
        "复制 report-template.json 填写实际观察，不修改模板或包。"
        "调用记录必须填写真实独立调用的身份、时间、读取文件和报告；"
        "空白模板不是真实调用。写出调用后计算摘要填入报告 invocation。\n",
        encoding="utf-8",
    )
    return target
