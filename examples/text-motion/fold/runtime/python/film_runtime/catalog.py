"""本作品保存的类型身份，不查询主项目类型注册表。"""
import json
from types import SimpleNamespace
from .core.assets import REPOSITORY_ROOT


class Catalog:
    def __init__(self):
        self.names = json.loads((REPOSITORY_ROOT / 'video-types.json').read_text(encoding='utf-8'))

    def has(self, name):
        return name in self.names

    def get(self, name):
        if not self.has(name):
            raise ValueError(f'未知类型：{name}')
        return SimpleNamespace(material_map=lambda: {'storyboard': 'storyboard.json'})


def catalog():
    return Catalog()
