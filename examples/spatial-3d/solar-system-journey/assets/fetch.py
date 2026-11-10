"""下载贴图、解包官方模型并生成原创材质，严格恢复登记的固定输入。"""
import logging
import subprocess
import sys
import tempfile
import zipfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from materials.generate import WIDTH, HEIGHT, material_rows, png
from materials.saturn import saturn_image
from film_runtime.core.example_media import digest, download, restore


@lru_cache(maxsize=2)
def model_archive(url, expected_sha256):
    """同一恢复批次只下载一次NASA原包；校验整包后才解出固定成员。"""
    with tempfile.TemporaryDirectory(prefix='m2v-nasa-model-') as temporary:
        source = Path(temporary) / 'model.bin'
        download(url, source)
        if digest(source) != expected_sha256:
            raise RuntimeError('NASA模型原包摘要不符；拒绝接受来源漂移')
        return source.read_bytes()


def generate(item, output):
    identity = item["id"]
    if identity in {"ceres", "ceres-normal"}:
        # 只读取登记成员，不把外部归档解压到文件系统；最终图片仍由restore校验。
        with zipfile.ZipFile(BytesIO(model_archive(item['archiveUrl'], item['archiveSha256']))) as archive:
            output.write_bytes(archive.read(item['archiveMember']))
    elif identity == "saturn":
        output.write_bytes(saturn_image(model_archive(item['archiveUrl'], item['archiveSha256'])))
    elif identity == "titan":
        png(output, WIDTH, HEIGHT, material_rows("titan", "color"))
    else:
        target, role = identity.rsplit("-", 1)
        png(output, WIDTH, HEIGHT, material_rows(target, role))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root = Path(__file__).resolve().parents[1]
    restore(root, generate)
    # 配乐同样是独立重建所需输入；只按固定配方恢复，拒绝覆盖已有摘要漂移。
    subprocess.run([sys.executable, str(root / 'assets/sound/generate.py'), '--restore'], check=True)
