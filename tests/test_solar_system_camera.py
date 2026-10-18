"""太阳系镜头数据：路径连续、单调向外、不穿天体，且 hero 绕目标画弧。

镜头几何现在写在分镜的 `shots[].camera.path` 里，因此这里验证的是**数据**，
而不是复制一份计算公式：天体布局仍从 `layout.tsx` 打包读取。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
STORYBOARD = ROOT / "examples/solar-system-journey/storyboard.json"

requires_node = pytest.mark.skipif(
    shutil.which("node") is None or not (WEB / "node_modules/esbuild").exists(),
    reason="镜头数据验证需要已安装的前端依赖")


@requires_node
def test_solar_shot_paths_are_continuous_outward_and_clear_of_bodies(tmp_path):
    script = r"""
import {build} from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const [repo, output] = process.argv.slice(1);
const web = path.join(repo, 'web');
const layout = path.join(repo, 'examples/solar-system-journey/scenes/layout.tsx');
const board = path.join(repo, 'examples/solar-system-journey/storyboard.json');
const entry = `
  import assert from 'node:assert/strict';
  import fs from 'node:fs';
  import {LAYOUT, positionOf} from ${JSON.stringify(layout)};
  const board = JSON.parse(fs.readFileSync(${JSON.stringify(board)}, 'utf8'));
  const shots = board.scenes[0].content.props.shots;
  const radius = (p) => Math.hypot(p[0], p[2]);
  const vec = (p) => ({x: p[0], y: p[1], z: p[2]});
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  const known = new Set([...Object.keys(LAYOUT), 'sun', 'heliopause', 'oort', 'sun-limb', 'inner-focus', 'ice-focus']);  // sun-limb / inner-focus / ice-focus 由场景的 focusTargets() 定义

  let previous = null, previousRadius = 0;
  for (const shot of shots) {
    const points = shot.camera?.path;
    assert(Array.isArray(points) && points.length >= 2, shot.id + ' 缺少镜头路径');
    for (const point of points) {
      assert(point.length === 3 && point.every(Number.isFinite), shot.id + ' 路径点不是有限三元组');
      for (const id of Object.keys(LAYOUT)) {
        const body = positionOf(id).toArray();
        assert(distance(point, body) > LAYOUT[id].radius * 1.05,
          '镜头路径穿过天体：' + shot.id + ' / ' + id + '（距离 ' + distance(point, body).toFixed(3) + '）');
      }
    }
    const entryRadius = radius(points[0]);
    const exitRadius = radius(points[points.length - 1]);
    if (previous) {
      if (shot.cut) {
        // 硬切：不接上一个镜头的出口，但只能向前跳，不能退回上一个镜头之前。
        assert(distance(previous, points[0]) > 1, shot.id + ' 声明了硬切，路径却仍然连着');
        assert(entryRadius >= previousRadius - 1e-6,
          shot.id + ' 的硬切入点回退：' + entryRadius.toFixed(2) + ' < ' + previousRadius.toFixed(2));
      } else {
        assert(distance(previous, points[0]) < 1e-6, shot.id + ' 与上一个镜头的路径不连续');
        assert(entryRadius >= previousRadius - 1e-6,
          shot.id + ' 的入口半径回退：' + entryRadius.toFixed(2) + ' < ' + previousRadius.toFixed(2));
      }
      assert(exitRadius >= previousRadius - 1e-6,
        shot.id + ' 的出口比上一个镜头更靠内：' + exitRadius.toFixed(2) + ' < ' + previousRadius.toFixed(2));
    }
    if ('cut' in shot) assert(shot.cut === true, shot.id + ' 的 cut 只能是 true');
    assert(['hero', 'major', 'minor'].includes(shot.tier), shot.id + ' 的 tier 非法');
    if (shot.focus?.target) assert(known.has(shot.focus.target), shot.id + ' 的焦点目标未知');
    if (shot.tier === 'hero') {
      const target = shot.focus?.target;
      const orbiting = target && LAYOUT[target] && LAYOUT[target].orbit > 0;
      if (orbiting) {
        assert(points.length >= 4, shot.id + ' 的 hero 镜头必须绕目标画弧（至少 4 个路径点）');
        const body = positionOf(target).toArray();
        const near = Math.min(...points.map(point => distance(point, body)));
        assert(near > LAYOUT[target].radius * 1.6, shot.id + ' 的 hero 离目标太近：' + near.toFixed(2));
        assert(near < 16, shot.id + ' 的 hero 离目标太远：' + near.toFixed(2));
        const far = Math.max(...points.map(point => distance(point, body)));
        assert(far - near > 0.5, shot.id + ' 的 hero 没有在目标周围产生位移');
      } else {
        // 不以环绕天体为焦点的 hero（太阳冷开场、奥尔特云拉远）：要求明显的单程位移。
        const last = points[points.length - 1];
        assert(radius(last) > radius(points[0]) * 1.4,
          shot.id + ' 的 hero 没有产生明显位移：' + radius(points[0]).toFixed(1) + ' → ' + radius(last).toFixed(1));
      }
    }
    previous = points[points.length - 1];
    previousRadius = radius(previous);
  }
  assert(!shots.some((shot) => 'cut' in shot), '太阳系样板要求几乎一镜到底，不应声明硬切');
  assert(previousRadius > 100, '全片结束时相机仍在太阳系内部：' + previousRadius.toFixed(1));
  assert(shots.filter((shot) => shot.tier === 'hero').length >= 3, 'hero 镜头少于 3 个');
  assert(positionOf('moon').distanceTo(positionOf('earth')) > LAYOUT.earth.radius + LAYOUT.moon.radius);
  assert(positionOf('titan').distanceTo(positionOf('saturn')) > LAYOUT.saturn.radius * 2.27 + LAYOUT.titan.radius);
`;
    await build({stdin: {contents: entry, resolveDir: web}, bundle: true, platform: 'node', format: 'cjs',
      outfile: output, nodePaths: [path.join(web, 'node_modules')],
      alias: {'m2v/code-scene': path.join(web, 'src/code-scene/sdk.tsx')}});
    createRequire(import.meta.url)(output);
"""
    result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", script,
                             str(ROOT), str(tmp_path / "camera.cjs")], cwd=WEB,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
