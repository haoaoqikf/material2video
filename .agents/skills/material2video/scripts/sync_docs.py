"""从类型目录和制作策略生成文档投影。

README、Skill 与项目规划曾各自维护一份类型清单，与代码里的清单互相独立、没有
任何一致性检查。现在它们由 `src/m2v/type_system/catalog.json` 生成，生成区域用成对
标记圈出，标记之外的内容保持手工维护。检查点文档的门表、风险表与审核人数表
分别由 production/workflow.py 和 production/policy.py 派生。

用法：

- `python sync_docs.py` 重新生成并写回有漂移的文档；
- `python sync_docs.py --check` 只比对，出现漂移时退出码为 1（用于验证与 CI）。

写回时保留每个文件原有的换行符，因此「重新生成」在 Windows 与 Linux 上都是幂等的。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
# 直接以脚本方式运行时也要能导入仓库内的 m2v 包。
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from m2v.core.errors import M2VError  # noqa: E402  依赖上面的 sys.path 处理

START_MARK = "<!-- generated:type-catalog:start -->"
END_MARK = "<!-- generated:type-catalog:end -->"

README = "README.md"
SKILL = ".agents/skills/material2video/SKILL.md"
PLAN = "docs/PROJECT_PLAN.md"


def _grouped_lines(catalog, render_entry, *, with_description: bool = False) -> list[str]:
    """先按类别登记顺序输出成员，再输出未分类类型；空行只分隔有内容的组。"""
    groups = [
        (category.title, category.description, catalog.types_in(category.id))
        for category in catalog.categories()
    ]
    uncategorized = catalog.uncategorized()
    if uncategorized:
        groups.append(("未分类", "", uncategorized))
    lines: list[str] = []
    for index, (title, description, entries) in enumerate(groups):
        if index:
            lines.append("")
        suffix = f"：{description}" if with_description and description else ""
        lines.append(f"**{title}**{suffix}")
        lines.extend(render_entry(entry) for entry in entries)
    return lines


def _readme_lines(catalog) -> list[str]:
    return _grouped_lines(catalog, lambda entry: f"- `{entry.name}`：{entry.summary}", with_description=True)


def _skill_lines(catalog) -> list[str]:
    lines = ["| 类别 | 类型 | 创作指导 |", "|---|---|---|"]
    for category in catalog.categories():
        lines.extend(
            f"| {category.title} | `{entry.name}` | {entry.skill_guide} |"
            for entry in catalog.types_in(category.id)
        )
    lines.extend(
        f"| 未分类 | `{entry.name}` | {entry.skill_guide} |"
        for entry in catalog.uncategorized()
    )
    return lines


def _plan_lines(catalog) -> list[str]:
    return _grouped_lines(catalog, lambda entry: f"- `{entry.name}`：{entry.plan}", with_description=True)


#: （相对路径，渲染函数）。渲染结果先按类别登记顺序、再按类型登记顺序输出。
TARGETS = ((README, _readme_lines), (SKILL, _skill_lines), (PLAN, _plan_lines))


def read_text(relative: str) -> tuple[str, str]:
    """读取文档：返回（换行统一为 ``\\n`` 的文本，文件原有的换行符）。"""
    path = REPO_ROOT / relative
    try:
        # newline="" 才能看到文件真实的换行符；Path.read_text 不接受该参数。
        with path.open("r", encoding="utf-8", newline="") as handle:
            raw = handle.read()
    except OSError as exc:
        raise M2VError(f"无法读取 {relative}: {exc}") from exc
    if "\r\n" in raw:
        return raw.replace("\r\n", "\n"), "\r\n"
    return raw, "\n"


def write_text(relative: str, text: str, newline: str) -> None:
    """按文件原有换行写回，避免把整份文档的换行风格改掉。"""
    body = text if newline == "\n" else text.replace("\n", newline)
    (REPO_ROOT / relative).write_text(body, encoding="utf-8", newline="")


def _inject(relative: str, text: str, lines: list[str], *, section="type-catalog") -> str:
    start_mark = f"<!-- generated:{section}:start -->"
    end_mark = f"<!-- generated:{section}:end -->"
    parts = text.split("\n")
    starts = [index for index, line in enumerate(parts) if line.strip() == start_mark]
    ends = [index for index, line in enumerate(parts) if line.strip() == end_mark]
    if len(starts) != 1 or len(ends) != 1:
        raise M2VError(
            f"{relative} 需要恰好一对生成标记，实际 start={len(starts)}、end={len(ends)}"
        )
    if ends[0] < starts[0]:
        raise M2VError(f"{relative} 的生成标记顺序颠倒")
    return "\n".join(parts[: starts[0] + 1] + lines + parts[ends[0] :])


CHECKPOINTS = ".agents/skills/material2video/references/checkpoint-gates.md"


def production_sections() -> dict[str, list[str]]:
    """可执行目录的文档视图；条件和人数不在文档脚本中重写。"""
    from m2v.production import policy, workflow

    gates = ["| 门 | 阶段 | 范围 | 检查方式 | 证据 |", "|---|---|---|---|---|"]
    gates.extend(f"| {g.id} | {g.phase} | {'检查点' if g.scope == 'checkpoint' else '全片'} | "
                 f"{'自动检查' if g.checker in ('declaration', 'design', 'mapping', 'capture') else '制作助手内部检查登记' if g.checker == 'internal' else '外部报告登记'} | {g.evidence} |" for g in workflow.GATES)
    risks = ["| kind | 门 | 额外要求 | 不触发的情况 |", "|---|---|---|---|"]
    risks.extend(f"| `{r.kind}` | {r.gate} | {r.evidence} | {r.excluded} |" for r in policy.RISK_CATALOG)
    core = '、'.join(f'`{r.kind}`' for r in policy.RISK_CATALOG if r.kind in policy.CORE_GATES)
    rounds = [f"核心审核风险：{core}。镜头等级不决定审核人数。", "",
              "| 审核计划 | 核心轮 | 粗片 | 终审 | 独立调用合计 |", "|---|---|---|---|---|"]
    # 从实际策略枚举核心风险与终审拆分的组合，避免手工计算调用次数。
    for has_core in (False, True):
        for split in (False, True):
            kinds = ([next(iter(policy.CORE_GATES))] if has_core else []) + (['split-final'] if split else [])
            value = policy.rounds({'reviewPlan': {'risks': [{'id': k, 'kind': k, 'reason': '策略示例', 'scope': {'checkpointIds': []}} for k in kinds]}})
            label = ('有核心风险' if has_core else '无核心风险') + ('，split-final' if split else '，常规终审')
            rounds.append(f"| {label} | {value['core']} | {value['rough']} | {value['final']} | {value['defaultCalls']} |")
    return {'production-gates': gates, 'review-risks': risks, 'review-rounds': rounds}


def build_outputs(catalog=None, *, include_production=True) -> dict[str, str]:
    """生成后的完整文档文本（换行为 ``\\n``），键是相对仓库根的路径。"""
    if catalog is None:
        from m2v.type_system import catalog as catalog_module

        catalog = catalog_module.catalog()
    entries = catalog
    outputs: dict[str, str] = {}
    for relative, render in TARGETS:
        text, _ = read_text(relative)
        outputs[relative] = _inject(relative, text, render(entries))
    if include_production:
        text, _ = read_text(CHECKPOINTS)
        for section, lines in production_sections().items():
            text = _inject(CHECKPOINTS, text, lines, section=section)
        outputs[CHECKPOINTS] = text
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按类型目录与制作策略生成文档投影")
    parser.add_argument("--check", action="store_true", help="只比对不写入，出现漂移时退出码为 1")
    args = parser.parse_args(argv)
    try:
        outputs = build_outputs()
        from guidance_docs import validate
        counts = validate(REPO_ROOT)
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    drifted: list[str] = []
    for relative, generated in outputs.items():
        current, newline = read_text(relative)
        if current == generated:
            continue
        drifted.append(relative)
        if not args.check:
            write_text(relative, generated, newline)
    if args.check and drifted:
        print(
            f"[error] 生成文档与权威来源不一致：{'、'.join(drifted)}；"
            f"运行 sync_docs.py 重新生成",
            file=sys.stderr,
        )
        return 1
    print("已更新：" + "、".join(drifted) if drifted else "生成文档与权威来源一致，无需改动")
    print('阅读预算（正文字符）：' + '、'.join(f'{key}={value}' for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
