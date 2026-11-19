"""保留的动效参考遵守确定性源码闸门。"""
from pathlib import Path

from film_runtime.core import source_policy

WEB = Path(__file__).resolve().parents[2] / "web"
COMPONENTS = WEB / "src/code-scene/motion-components"


def test_shared_components_pass_the_determinism_source_gate():
    files = sorted(path for path in COMPONENTS.iterdir()
                   if path.suffix in {".ts", ".tsx"} and ".test." not in path.name)
    assert files
    violations = source_policy.scan(files)
    assert not violations, [item.render(WEB) for item in violations]
