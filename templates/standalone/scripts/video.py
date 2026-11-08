"""本工程的直接运行入口；依赖由本目录的uv.lock恢复，不需要主项目。"""
from film_runtime.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
