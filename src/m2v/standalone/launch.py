"""只用标准库的启动屏障：父工具完成进程树归属后才释放实际作品命令。"""
import json
import os
import subprocess
import sys


def main() -> int:
    # stdin只传一条参数数组，实际作品stdin关闭；不经过shell或执行拼接字符串。
    payload = json.loads(sys.stdin.readline())
    process = subprocess.Popen(payload['argv'], stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
    return process.wait()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f'无法启动作品本地命令：{error}', file=sys.stderr, flush=True)
        raise SystemExit(1)
