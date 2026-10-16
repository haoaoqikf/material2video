"""校验报告：类型校验与契约检查共用的结果载体。

`Issue` 与 `Report` 是「错误路径指向 JSON 字段、警告默认放行」这一套语义的
唯一定义。分镜、媒体清单、声音契约、作品清单的校验都返回它，
调用方（`m2v validate`、准备与渲染入口）只按 `ok` / `errors` / `warnings` 判断，
不需要知道校验器是谁。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Issue:
    """一条校验结果。path 指向 JSON 内的层级位置，便于 AI 定位修正。"""

    level: str  # "error" 或 "warning"
    path: str  # 例如 "scenes[2].renderer.module"
    message: str

    def format(self) -> str:
        return f"[{self.level}] {self.path}: {self.message}"


@dataclass
class Report:
    """校验报告：errors 不通过则禁止渲染，warnings 默认放行。"""

    issues: list[Issue] = field(default_factory=list)

    def add(self, level: str, path: str, message: str) -> None:
        self.issues.append(Issue(level, path, message))

    def error(self, path: str, message: str) -> None:
        self.add("error", path, message)

    def warn(self, path: str, message: str) -> None:
        self.add("warning", path, message)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [{"path": i.path, "message": i.message} for i in self.errors],
            "warnings": [{"path": i.path, "message": i.message} for i in self.warnings],
        }
