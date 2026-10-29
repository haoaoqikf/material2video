"""恢复固定媒体；已登记且摘要一致的本地文件直接复用。"""
import logging
from pathlib import Path
from m2v.core.example_media import restore

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    restore(Path(__file__).resolve().parents[1])
