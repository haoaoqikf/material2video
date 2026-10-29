/** 对运行时相机逐帧量测；技术测量不自动生成审美通过结论。 */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const root = path.resolve(import.meta.dirname, '..');
const web = path.resolve(root, '../../web');
const require = createRequire(path.join(web, 'package.json'));
const {build} = require('esbuild');
const output = path.join(root, 'outputs/motion-runtime.cjs');
await build({stdin: {contents: `
import {createFlight} from ${JSON.stringify(path.join(root, 'scenes/flight.ts'))};
import {LAYOUT, positionOf} from ${JSON.stringify(path.join(root, 'scenes/layout.tsx'))};
module.exports = {createFlight, LAYOUT, positionOf};`, resolveDir: web}, bundle: true,
  platform: 'node', format: 'cjs', outfile: output, nodePaths: [path.join(web, 'node_modules')],
  alias: {'m2v/code-scene': path.join(web, 'src/code-scene/sdk.tsx')}});
const {createFlight, LAYOUT, positionOf} = require(output);
const board = JSON.parse(fs.readFileSync(path.join(root, 'storyboard.json'), 'utf8'));
const scene = board.scenes[0], fps = board.fps;
const proposal = JSON.parse(fs.readFileSync(path.join(root, 'outputs/path-proposal.json'), 'utf8'));
const targets = Object.fromEntries(Object.keys(LAYOUT).map(id => [id, positionOf(id)]));
// 优先使用实际准备的旁白窗口；没有准备产物时才退回路径预算窗口。
const signature = items => JSON.stringify((items ?? []).map(item => [item.id, item.text]));
const preparedPath = path.join(root, 'outputs/prepared.json');
let windows = null, windowSource = null;
if (fs.existsSync(preparedPath)) {
  const prepared = JSON.parse(fs.readFileSync(preparedPath, 'utf8'));
  const compiled = prepared.props?.compiledScenes?.[0];
  if (prepared.durationInFrames === scene.durationFrames && compiled?.segmentWindows) {
    if (signature(compiled.narrationSegments) !== signature(scene.narrationSegments)) {
      throw new Error('prepared 与当前 storyboard 旁白不一致；请重新 prepare');
    }
    const offset = compiled.startFrame ?? 0;
    windows = Object.fromEntries(Object.entries(compiled.segmentWindows).map(([id, window]) =>
      [id, {startFrame: window.startFrame + offset, endFrame: window.endFrame + offset}]));
    windowSource = 'prepared';
  }
}
if (!windows) {
  windows = proposal.report.windows;
  windowSource = 'path-proposal';
  if (signature(proposal.storyboard?.scenes?.[0]?.narrationSegments)
      !== signature(scene.narrationSegments)) {
    throw new Error('path-proposal 与当前 storyboard 旁白不一致；请重新运行 generate-paths.mjs --merge');
  }
}
// 障碍与外层结构半径由生成器输出，避免诊断、生成器和测试各自维护一份几何。
const obstacles = proposal.report.obstacles;
const structureRadius = proposal.report.structureRadius;
if (!Array.isArray(obstacles) || !obstacles.length || !structureRadius) {
  throw new Error('path-proposal 缺少 obstacles/structureRadius；请重新运行 generate-paths.mjs');
}
const shots = scene.content.props.shots;
const shotAt = frame => shots.find(shot => frame >= shot.startFrame && frame < shot.endFrame);
const sample = createFlight(shots, windows, targets);
let previous = sample(0), velocity = null;
const report = {scope: 'technical-motion-measurements', observation: 'not-evaluated',
  frames: scene.durationFrames, windowSource, maxAngularSpeed: 0, maxAcceleration: 0, maxFovStep: 0,
  minClearance: Infinity, angularPeaks: [], shotScales: {}, trajectory: [], problems: []};
for (const shot of shots) report.shotScales[shot.id] = {target: shot.target,
  startFrame: shot.startFrame, endFrame: shot.endFrame,
  minScale: Infinity, maxScale: 0, maxScaleStep: 0, previousScale: null};
for (let frame = 1; frame < scene.durationFrames; frame++) {
  const pose = sample(frame);
  const step = pose.position.clone().sub(previous.position).multiplyScalar(fps);
  const angularSpeed = pose.quaternion.angleTo(previous.quaternion) * 180 / Math.PI * fps;
  if (angularSpeed > report.maxAngularSpeed) report.maxAngularSpeed = angularSpeed;
  if (angularSpeed > 35) report.angularPeaks.push({frame, seconds: frame / fps, angularSpeed});
  if (velocity) report.maxAcceleration = Math.max(report.maxAcceleration,
    step.clone().sub(velocity).length() * fps);
  const fovStep = Math.abs(pose.fov - previous.fov) * fps;
  report.maxFovStep = Math.max(report.maxFovStep, fovStep);
  for (const obstacle of obstacles) {
    const clearance = Math.hypot(pose.position.x - obstacle.center[0],
      pose.position.y - obstacle.center[1], pose.position.z - obstacle.center[2]) - obstacle.radius;
    report.minClearance = Math.min(report.minClearance, clearance);
  }
  // 主体屏幕尺度 = 目标直径占画面高度的比例；只在覆盖该主体的镜头内统计。
  const shot = shotAt(frame);
  const subjectRadius = shot && (LAYOUT[shot.target]?.radius ?? structureRadius[shot.target]);
  if (shot && subjectRadius) {
    const entry = report.shotScales[shot.id];
    const distance = Math.max(1e-6, pose.position.distanceTo(targets[shot.target] ?? targets.sun));
    const scale = subjectRadius / (distance * Math.tan(pose.fov * Math.PI / 360));
    entry.minScale = Math.min(entry.minScale, scale);
    entry.maxScale = Math.max(entry.maxScale, scale);
    if (entry.previousScale !== null)
      entry.maxScaleStep = Math.max(entry.maxScaleStep, Math.abs(scale - entry.previousScale) * fps);
    entry.previousScale = scale;
  }
  if (![...pose.position.toArray(), ...pose.quaternion.toArray(), pose.fov].every(Number.isFinite))
    report.problems.push(`non-finite at ${frame}`);
  if (frame % 15 === 0) report.trajectory.push({frame, position: pose.position.toArray(),
    quaternion: pose.quaternion.toArray(), speed: step.length(), angularSpeed, fov: pose.fov});
  previous = pose; velocity = step;
}
for (const entry of Object.values(report.shotScales)) delete entry.previousScale;
if (report.minClearance < 0.4) report.problems.push('filtered camera crosses clearance');
fs.writeFileSync(path.join(root, 'outputs/motion-report.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({...report, shotScales: `${Object.keys(report.shotScales).length} shots`,
  angularPeaks: report.angularPeaks.sort((a,b) => b.angularSpeed-a.angularSpeed).slice(0,8),
  trajectory: `${report.trajectory.length} samples`}, null, 2));
if (report.problems.length) process.exitCode = 1;
