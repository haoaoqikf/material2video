"""太阳系镜头数据：逐站停留、幕内连续、不穿天体，且 hero 有持续运动。

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
  import {THREE} from 'm2v/code-scene';
  const board = JSON.parse(fs.readFileSync(${JSON.stringify(board)}, 'utf8'));
  const shots = board.scenes.flatMap(scene => scene.content.props.shots);
  const scenes = board.scenes;
  const radius = (p) => Math.hypot(p[0], p[2]);
  const vec = (p) => ({x: p[0], y: p[1], z: p[2]});
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  const known = new Set([...Object.keys(LAYOUT), 'sun', 'heliopause', 'oort', 'sun-limb', 'kuiper']);  // sun-limb / inner-focus / ice-focus 由场景的 focusTargets() 定义

  let previousRadius = 0;
  for (const scene of scenes) {
    const shots = scene.content.props.shots;
    assert(scene.narrationSegments.length === 1, '每个主体必须独立介绍');
    assert(scene.tailFrames >= 45, '必须保留明确观察窗口');
    assert(scene.content.props.body, '主体身份必须来自语义配置');
    for (const shot of shots) {
    const points = shot.camera?.path;
    assert(Array.isArray(points) && points.length >= 2, shot.id + ' 缺少镜头路径');
    // Sample the actual spline rather than checking control points alone.
    const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)), false, 'catmullrom', .5);
    for (let sample = 0; sample <= 120; sample++) {
      const point = curve.getPoint(sample / 120).toArray();
      assert(point.every(Number.isFinite), shot.id + ' 无效坐标');
      for (const id of Object.keys(LAYOUT)) {
        const body = positionOf(id).toArray();
        assert(distance(point, body) > LAYOUT[id].radius * 1.05,
          '镜头穿过天体：' + shot.id + ' / ' + id);
      }
    }
    const exitRadius = radius(points[points.length - 1]);
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
        assert(distance(points[0], points[points.length - 1]) > LAYOUT[target].radius * .1, shot.id + ' 的 hero 没有位移');
      } else {
        // 不以环绕天体为焦点的 hero（太阳冷开场、奥尔特云拉远）：要求明显的单程位移。
        const last = points[points.length - 1];
        assert(radius(last) > radius(points[0]) * 1.4,
          shot.id + ' 的 hero 没有产生明显位移：' + radius(points[0]).toFixed(1) + ' → ' + radius(last).toFixed(1));
      }
    }
    previousRadius = exitRadius;
    }
  }
  assert(scenes.slice(1).every(scene => scene.transition === 'crossfade' && scene.transitionFrames >= 30), '跨尺度切换必须留足慢叠化');
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
