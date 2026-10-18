"""单幕一镜到底的镜头数据：连续覆盖、首尾相接、不穿天体、边界不跳速。

镜头几何现在写在分镜的 `shots[].camera.path` 里，因此这里验证的是**数据**，
而不是复制一份计算公式：天体布局仍从 `layout.tsx` 打包读取。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
STORYBOARD = ROOT / "examples/solar-system-journey/storyboard.json"

#: 与 outputs/prepared.json 一致的实测 TTS 帧长；文本或语速改变时必须同步本表。
SEGMENT_FRAMES = [309, 300, 285, 297, 289, 313, 225, 373, 339, 294, 316, 307, 216, 356, 332]

requires_node = pytest.mark.skipif(
    shutil.which("node") is None or not (WEB / "node_modules/esbuild").exists(),
    reason="镜头数据验证需要已安装的前端依赖")


@requires_node
def test_solar_one_take_paths_are_continuous_clear_and_smooth(tmp_path):
    script = r"""
import {build} from 'esbuild';
import path from 'node:path';
import {createRequire} from 'node:module';
const [repo, output] = process.argv.slice(1);
const web = path.join(repo, 'web');
const layout = path.join(repo, 'examples/solar-system-journey/scenes/layout.tsx');
const board = path.join(repo, 'examples/solar-system-journey/storyboard.json');
const frames = process.env.SEGMENT_FRAMES;
const entry = `
  import assert from 'node:assert/strict';
  import fs from 'node:fs';
  import {LAYOUT, positionOf} from ${JSON.stringify(layout)};
  import {THREE} from 'm2v/code-scene';
  const board = JSON.parse(fs.readFileSync(${JSON.stringify(board)}, 'utf8'));
  const segmentFrames = ${frames};
  const scenes = board.scenes;
  assert.equal(scenes.length, 1, '一镜到底必须只有一幕');
  const scene = scenes[0];
  assert.equal(scene.id, 'solar-journey');
  assert.equal(scene.durationFrames, 8100);
  assert.equal(scene.transition, 'cut');
  assert.equal(scene.leadInFrames, 360);
  assert.equal(scene.tailFrames, 669);
  assert.equal(scene.narrationSegments.length, 15);
  assert(scene.narrationSegments.slice(0, -1).every(item => item.holdFrames === 180),
    '前 14 段必须有 3 秒段间留白');
  assert(!('holdFrames' in scene.narrationSegments.at(-1)), '最后一段不得声明段间留白');
  const shots = scene.content.props.shots;
  assert.equal(shots.length, 28, '镜头数必须是 28');
  assert.equal(shots[0].startFrame, 0);
  assert.equal(shots.at(-1).endFrame, 8100);
  for (let index = 1; index < shots.length; index += 1) {
    assert.equal(shots[index].startFrame, shots[index - 1].endFrame, '镜头时间窗必须首尾相接');
  }
  assert(shots.every(shot => !shot.cut), '一镜到底不允许硬切');
  assert(shots.every(shot => shot.camera?.easing === 'linear'),
    '线性缓动是边界不停顿的前提；sineInOut 会让每个镜头边界速度归零');

  // 由实测 TTS 帧长重建旁白窗口，逐段检查有且只有一个覆盖镜头。
  const windows = {};
  let cursor = 360;
  scene.narrationSegments.forEach((segment, index) => {
    windows[segment.id] = {startFrame: cursor, endFrame: cursor + segmentFrames[index]};
    cursor += segmentFrames[index] + (index < segmentFrames.length - 1 ? 180 : 0);
  });
  assert.equal(cursor, 7431, '旁白末帧必须落在尾留白起点');
  for (const segment of scene.narrationSegments) {
    const covering = shots.filter(shot => shot.segment === segment.id);
    assert.equal(covering.length, 1, segment.id + ' 必须有且只有一个覆盖镜头');
    assert(covering[0].startFrame <= windows[segment.id].startFrame
      && covering[0].endFrame >= windows[segment.id].endFrame, segment.id + ' 没有覆盖旁白窗口');
  }

  const heroes = shots.filter(shot => shot.tier === 'hero');
  assert(heroes.length >= 3, 'hero 镜头少于 3 个');
  for (const hero of heroes) {
    const length = hero.endFrame - hero.startFrame;
    assert(length >= 480 && length <= 720, hero.id + ' hero 必须 8～12 秒，实际 ' + length);
  }

  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  const curveOf = points => new THREE.CatmullRomCurve3(
    points.map(point => new THREE.Vector3(...point)), false, 'catmullrom', 0.5);
  const position = (shot, frame) => {
    const span = Math.max(1, shot.endFrame - shot.startFrame);
    return curveOf(shot.camera.path).getPoint(
      Math.min(1, Math.max(0, (frame - shot.startFrame) / span))).toArray();
  };

  for (let index = 0; index < shots.length; index += 1) {
    const shot = shots[index];
    const points = shot.camera?.path;
    assert(Array.isArray(points) && points.length >= 2 && points.length <= 64, shot.id + ' 路径点数非法');
    if (index) {
      const gap = dist(shots[index - 1].camera.path.at(-1), points[0]);
      assert(gap < 1e-6, shot.id + ' 与前镜头位置不连续：' + gap);
    }
    const curve = curveOf(points);
    for (let sample = 0; sample <= 240; sample += 1) {
      const point = curve.getPoint(sample / 240).toArray();
      assert(point.every(Number.isFinite), shot.id + ' 无效坐标');
      assert(Math.hypot(...point) < 900, shot.id + ' 越出星空壳');
      for (const id of Object.keys(LAYOUT)) {
        const body = positionOf(id).toArray();
        const radius = id === 'sun' ? LAYOUT.sun.radius * 1.5
          : id === 'saturn' ? LAYOUT.saturn.radius * 2.27 : LAYOUT[id].radius * 1.05;
        const gap = dist(point, body) - radius - 0.4;
        assert(gap > 0, shot.id + ' 穿过 ' + id + '：余量 ' + gap.toFixed(2));
      }
    }
  }

  // 开场必须从系统上方出发，并在第一个旁白窗口前抵达太阳附近。
  const open = shots[0].camera.path;
  assert(open[0][1] > 250 && Math.hypot(...open[0]) > 250,
    '开场不在太阳系上方：' + open[0]);
  assert(Math.hypot(...open.at(-1)) < 15, '开场没有抵达太阳');
  assert(shots[0].camera.fov >= 50, '开场需要更宽的视野容纳整个系统');

  // 主序天体必须按轨道半径单调向外排列，形成连续螺旋。
  const order = ['mercury', 'venus', 'earth', 'mars', 'ceres', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
  for (let index = 1; index < order.length; index += 1) {
    const previous = LAYOUT[order[index - 1]];
    const current = LAYOUT[order[index]];
    assert(current.orbit > previous.orbit, order[index] + ' 轨道半径没有向外递增');
    assert(current.angle > previous.angle, order[index] + ' 方位角没有递增');
  }
  assert(positionOf('moon').distanceTo(positionOf('earth')) > LAYOUT.earth.radius + LAYOUT.moon.radius);
  assert(positionOf('titan').distanceTo(positionOf('saturn')) > LAYOUT.saturn.radius * 2.27 + LAYOUT.titan.radius);

  // 镜头边界不得出现停顿或跳速。
  for (let index = 1; index < shots.length; index += 1) {
    const previous = shots[index - 1];
    const current = shots[index];
    const before = dist(position(previous, current.startFrame - 5),
      position(previous, current.startFrame - 1)) / 4;
    const after = dist(position(current, current.startFrame + 1),
      position(current, current.startFrame + 5)) / 4;
    const ratio = Math.max(before, after) / Math.max(1e-6, Math.min(before, after));
    assert(ratio < 1.9, previous.id + ' → ' + current.id + ' 速度突变 ×' + ratio.toFixed(2));
  }
`;
    await build({stdin: {contents: entry, resolveDir: web}, bundle: true, platform: 'node', format: 'cjs',
      outfile: output, nodePaths: [path.join(web, 'node_modules')],
      alias: {'m2v/code-scene': path.join(web, 'src/code-scene/sdk.tsx')}});
    createRequire(import.meta.url)(output);
"""
    environment = {**os.environ, "SEGMENT_FRAMES": json.dumps(SEGMENT_FRAMES)}
    result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", script,
                             str(ROOT), str(tmp_path / "camera.cjs")], cwd=WEB, env=environment,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
