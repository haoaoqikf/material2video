"""技术候选与制作完成分别报告。"""


def summary(result):
    complete = result["production"].get("complete", False)
    if result.get("candidate", {}).get("status") == "delivered":
        return "候选已生成，制作复核完成" if complete else "候选已生成，制作未完成"
    return "制作证据已齐，候选尚未交付" if complete else "制作未完成，候选尚未交付"
