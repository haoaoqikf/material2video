"""下载观测图并生成原创材质，严格恢复登记的固定输入。"""
import logging
from pathlib import Path
from materials.generate import WIDTH, HEIGHT, material_rows, ring_rows, png
from m2v.core.example_media import restore


def generate(item, output):
    identity = item["id"]
    if identity == "rings":
        png(output, WIDTH, 512, ring_rows())
    elif identity == "titan":
        png(output, WIDTH, HEIGHT, material_rows("titan", "color"))
    else:
        target, role = identity.rsplit("-", 1)
        png(output, WIDTH, HEIGHT, material_rows(target, role))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    restore(Path(__file__).resolve().parents[1], generate)
