"""统一的可预期错误基类。

配音准备、媒体校验、浏览器契约、编码与渲染编排都会主动抛错。
如果它们各自继承不同的基类，CLI 就必须逐个枚举才能把
「用户可修正的问题」渲染成一行提示，漏掉一个就会打印 Python 栈。

因此这里定义单一基类：所有「预期内的失败」都继承它，CLI 只捕获它一次。
程序缺陷（TypeError、KeyError 等）不在此列，仍应完整暴露栈信息。
"""

from __future__ import annotations


class A2VError(RuntimeError):
    """渲染链路上所有可预期失败的基类。"""
