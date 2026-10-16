"""真实太阳系镜头数学：检查段边界连续、固定布局和近景避碰，不靠源码字符串推断。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


@pytest.mark.skipif(shutil.which("node") is None or not (WEB / "node_modules/esbuild").exists(),
                    reason="镜头数学验证需要已安装的前端依赖")
def test_solar_camera_is_continuous_and_clear_of_bodies(tmp_path):
    # 从实际 TSX 打包纯相机函数；不替身实现轨迹或复制其计算公式。
    script = r"""
import {build} from 'esbuild';
import path from 'node:path';
import {createRequire} from 'node:module';
const [repo, output] = process.argv.slice(1);
const web = path.join(repo, 'web');
const layout = path.join(repo, 'examples/solar-system-journey/scenes/layout.tsx');
const entry = `
  import assert from 'node:assert/strict';
  import {LAYOUT, positionOf, poseAt} from ${JSON.stringify(layout)};
  const ids = [...Object.keys(LAYOUT), 'heliopause', 'oort'];
  const stops = ids.map((id,i)=>({id,start:i*10,end:(i+1)*10}));
  for (let i=1;i<stops.length;i++) {
    const t=stops[i].start;
    const left=poseAt(stops,i-1,t-0.00001), right=poseAt(stops,i,t+0.00001);
    assert(left.eye.distanceTo(right.eye)<0.001, '相机位置在段边界跳变：'+ids[i]);
    assert(left.target.distanceTo(right.target)<0.001, '相机朝向在段边界跳变：'+ids[i]);
  }
  for (let i=0;i<ids.length;i++) {
    for(let t=stops[i].start;t<stops[i].end;t+=0.1) {
      const pose=poseAt(stops,i,t);
      assert([...pose.eye.toArray(),...pose.target.toArray()].every(Number.isFinite));
      assert(pose.eye.distanceTo(pose.target)>0.1);
      for (const id of Object.keys(LAYOUT)) {
        assert(pose.eye.distanceTo(positionOf(id))>LAYOUT[id].radius*1.05,
          '镜头穿过天体：'+ids[i]+' / '+id);
      }
    }
    if (LAYOUT[ids[i]]) {
      const pose=poseAt(stops,i,stops[i].start+5);
      assert(pose.target.distanceTo(positionOf(ids[i]))<0.001);
    }
  }
  assert(positionOf('moon').distanceTo(positionOf('earth'))>LAYOUT.earth.radius+LAYOUT.moon.radius);
  assert(positionOf('titan').distanceTo(positionOf('saturn'))>LAYOUT.saturn.radius*2.27+LAYOUT.titan.radius);
`;
await build({stdin:{contents:entry,resolveDir:web},bundle:true,platform:'node',format:'cjs',
  outfile:output,nodePaths:[path.join(web,'node_modules')],
  alias:{'m2v/code-scene':path.join(web,'src/code-scene/sdk.tsx')}});
createRequire(import.meta.url)(output);
"""
    result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", script,
                             str(ROOT), str(tmp_path / "camera.cjs")], cwd=WEB,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
