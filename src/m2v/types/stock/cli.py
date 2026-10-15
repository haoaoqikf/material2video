"""``m2v stock`` 子命令：在线素材检索与下载。

检索是 prepare 之前的独立步骤：它需要联网与凭据，而准备、预演与渲染必须离线
可重复执行。命令只做检索与留证，不写准备记录，因此不会让已有评审意外失效——
但检索记录本身是准备输入，重新检索后必须重新准备与完整预演。
"""
from __future__ import annotations

import argparse
import sys

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.types.stock import search as search_module


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v stock", description="在线素材检索与下载")
    parser.add_argument("workflow", choices=("search",))
    parser.add_argument("--project", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=None,
                        help="单次网络请求超时（秒），省略时使用类型默认值")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root, manifest = load_project(args.project)
        if manifest["type"] != "stock-montage":
            raise M2VError("m2v stock 仅适用于 stock-montage 作品")
        options = {} if args.timeout_seconds is None else {"timeout_s": args.timeout_seconds}
        record = search_module.search(root, manifest, **options)
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    print(f"已检索 {len(record['scenes'])} 幕素材（图库：{record['provider']['name']}）")
    for entry in record["scenes"]:
        asset = entry["asset"]
        print(f"  {entry['id']}：{asset['path']}（{asset['kind']}，{asset['author']}，{asset['license']}）")
    print(f"检索记录：{search_module.record_path(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
