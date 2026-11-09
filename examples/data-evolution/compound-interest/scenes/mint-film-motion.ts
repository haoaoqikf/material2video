/** 六段共用显式帧、稳定资本身份及同一实体层；不运行累计模拟。 */
import {easeMotion} from '../src/code-scene/motion';
import {clamp} from './compoundMath';
import {annualSnapshot, coreFrame, FILM_DURATION_FRAMES, growthFrame, MINT, moveCoin, transitionYear} from './capital-motion';
import type {FilmClock} from './capital-motion';
import {designFrame} from './capital-state';
import type {Camera, CapitalFrame, Token} from './capital-state';
import {CAPITAL_STYLE, RESULT_LAYOUT} from './capital-style';

const smooth = (p: number) => easeMotion('easeInOutCubic', clamp(p));
const out = (p: number) => easeMotion('easeOutCubic', clamp(p));
const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
const palette = {background: MINT.background, floor: MINT.floor};
const principal = designFrame(1).tokens.slice(0, 10).map(item => ({...item, x: 960}));
function cameraBetween(a: Camera, b: Camera, p: number): Camera {
  return {x: lerp(a.x, b.x, p), y: lerp(a.y, b.y, p), scale: lerp(a.scale, b.scale, p),
    elevation: lerp(a.elevation ?? 0, b.elevation ?? 0, p)};
}
function groundCamera(scale: number, x = 960, base = MINT.base): Camera {
  const elevation = .65;
  const focusY = CAPITAL_STYLE.floorY + ((base - 540) / scale
    - RESULT_LAYOUT.rowDepth * Math.sin(elevation)) / Math.cos(elevation);
  return {x, y: 1080 - focusY, scale, elevation};
}
function fitGroups(state: CapitalFrame, scale: number): CapitalFrame {
  return {...state, camera: groundCamera(scale), tokens: state.tokens.map(item => {
    const screenX = item.id.startsWith('l-') ? MINT.left : MINT.right;
    const dx = (screenX - 960) * (1 / scale - 1 / MINT.scale);
    return {...item, x: item.x + dx};
  })};
}
export function filmPhase(clock: FilmClock) {
  if (clock.passed('close-start')) return 'closing';
  if (clock.passed('result')) return 'result';
  if (clock.passed('growth-start')) return 'growth';
  if (clock.passed('compare-start')) return 'split';
  if (clock.passed('core-start')) return 'core';
  if (clock.passed('first-start')) return 'first';
  return 'opening';
}
function openingCamera(clock: FilmClock): Camera {
  const scale = 4 + .1 * smooth(clock.frame / clock.at('first-start'));
  const elevation = .6;
  return {x: 960, y: 1080 - (CAPITAL_STYLE.floorY + 340 / (scale * Math.cos(elevation))), scale, elevation};
}
function openingFrame(clock: FilmClock): CapitalFrame {
  const tokens = [MINT.left, MINT.right].flatMap((center, group) => principal.map((item, i) => {
    const land = clock.at(`drop-${i + 1}`);
    const progress = out((clock.frame - land + 10) / 10);
    const since = Math.max(0, (clock.frame - land) / clock.fps);
    const rebound = Math.sin(since * 22) * 1.4 * Math.exp(-since * 12);
    return {...item, id: `${group ? 'r' : 'l'}-${i}`, x: 960 + (center - 960) / 4,
      y: item.y - 30 * (1 - progress) - rebound, opacity: clamp(progress * 4)};
  }));
  return {tokens, camera: openingCamera(clock), palette, phase: 'opening', time: clock.frame / clock.fps};
}
function firstFrame(clock: FilmClock): CapitalFrame {
  const core = coreFrame(clock.atFrame(clock.at('core-start')));
  const pan = smooth(clock.progress('first-start', 'first-formed'));
  const nearCamera = cameraBetween(openingCamera(clock.atFrame(clock.at('first-start'))),
    {...core.camera, scale: 5.2}, pan);
  const showcase = smooth(clock.progress('first-formed', 'first-hover'));
  const returnPose = smooth(clock.progress('first-hover', 'core-start'));
  nearCamera.scale -= .15 * smooth(clock.progress('first-formed', 'core-start'));
  const camera = cameraBetween(nearCamera, core.camera, returnPose);
  const tokens = principal.map(item => ({...item, x: item.x + 100 * (1 - pan)}));
  tokens.push(...principal.map((item, i) => ({...item, id: `l-${i}`, x: 840 - 100 * pan, opacity: 1 - pan})));
  const birth = out(clock.progress('first-birth', 'first-formed'));
  if (birth > 0) {
    const target = core.tokens[10], parent = tokens[9];
    const source = {...target, x: parent.x, y: parent.y - 5, units: 0, opacity: 0,
      pitch: -Math.PI / 2, tilt: 0};
    const coin = moveCoin(source, {...target, x: target.x + 100 * (1 - pan)}, birth);
    coin.pitch = (coin.pitch ?? 0) - .25 * showcase * (1 - returnPose);
    coin.tilt += .25 * showcase * (1 - returnPose);
    tokens.push(coin);
  }
  return {...core, tokens, camera, phase: 'opening', time: clock.frame / clock.fps};
}
function reframe(from: CapitalFrame, to: CapitalFrame, progress: number): CapitalFrame {
  const a = new Map(from.tokens.map(item => [item.id, item]));
  const b = new Map(to.tokens.map(item => [item.id, item]));
  const ids = new Set([...a.keys(), ...b.keys()]);
  const tokens = [...ids].map(id => {
    const left = a.get(id), right = b.get(id);
    return moveCoin(left ?? {...right!, units: 0, opacity: 0}, right ?? {...left!, units: 0, opacity: 0}, progress);
  }).filter(item => item.units > 1e-8);
  return {...to, tokens, camera: cameraBetween(from.camera, to.camera, progress)};
}
/** 第2年两路同步分流，再同时产生第3年收益，接入年度快进。 */
function splitFrame(clock: FilmClock): CapitalFrame {
  const commit = clock.progress('split-start', 'split-contact');
  const birth = clock.progress('third-birth', 'third-formed');
  const flight = out(clock.progress('third-formed', 'third-contact'));
  const state = fitGroups(transitionYear(3, commit, birth), 3.2);
  const snapshot = fitGroups(annualSnapshot(2), 3.2);
  const leftTop = snapshot.tokens.find(item => item.id === 'l-9')!;
  state.tokens = state.tokens.map(item => {
    if (item.id !== 'l-11' && item.id !== 'l-12') return item;
    const previous = item.id === 'l-11', progress = previous ? smooth(commit) : flight;
    const source = {...leftTop, id: item.id, y: leftTop.y - 35, gold: 1,
      tone: 'gold' as const, pitch: -1.0, tilt: -.2};
    const moved = moveCoin(source, item, progress);
    return {...moved, y: moved.y - 22 * Math.sin(Math.PI * progress),
      units: previous ? 1 : out(birth), opacity: previous ? 1 : out(birth),
      gold: 1 - smooth((progress - .65) / .35), tone: 'dark'};
  });
  const oldCore = coreFrame(clock.atFrame(clock.at('compare-start') - 1));
  const from = {...oldCore, tokens: [...oldCore.tokens,
    ...snapshot.tokens.filter(item => item.id.startsWith('l-')).map(item => ({...item, x: item.x - 850}))]};
  return {...reframe(from, state, smooth(clock.progress('compare-start', 'compare-ready'))),
    time: clock.frame / clock.fps};
}
function closingFrame(clock: FilmClock): CapitalFrame {
  const state = annualSnapshot(30), right = state.tokens.filter(item => !item.id.startsWith('l-'));
  const gains = right.filter(item => item.id.startsWith('gain-30-'));
  const lifts = new Map(gains.map(item => {
    const index = Number(item.id.split('-').at(-1)), contact = clock.at(`close-${index + 1}`);
    const progress = smooth((clock.frame - contact + 12) / 12);
    return [item.id, {progress, height: 12 * Math.sin(Math.PI * progress)}] as const;
  }));
  const tokens = right.map(item => {
    if (!item.id.startsWith('gain-30-')) return item;
    const lift = lifts.get(item.id)!;
    // 同列上层由下层承载，不能在下层抬升时停在原处造成实体穿插。
    const carried = gains.filter(other => other.x === item.x && other.z === item.z && other.y > item.y)
      .reduce((sum, other) => sum + lifts.get(other.id)!.height, 0);
    const gold = 1 - smooth((lift.progress - .65) / .35);
    return {...item, y: item.y - lift.height - carried, gold,
      tone: (gold <= 1e-8 ? 'white' : 'gold') as Token['tone']};
  });
  const center = 960 + (MINT.right - 960) / MINT.scale;
  const pull = smooth(clock.progress('close-return', 'conclusion'));
  const after = smooth((clock.frame - clock.at('conclusion')) / (FILM_DURATION_FRAMES - clock.at('conclusion')));
  const camera = cameraBetween({x: center, y: 810, scale: 3.3, elevation: .65},
    groundCamera(2.3 + .06 * after, center), pull);
  return {...state, tokens, camera, time: clock.frame / clock.fps};
}
export function fullFrame(clock: FilmClock): CapitalFrame {
  switch (filmPhase(clock)) {
    case 'opening': return openingFrame(clock);
    case 'first': return firstFrame(clock);
    case 'core': return coreFrame(clock);
    case 'split': return splitFrame(clock);
    case 'growth': {
      const pull = smooth(clock.progress('year-20', 'result'));
      return fitGroups(growthFrame(clock), lerp(3.2, MINT.scale, pull));
    }
    case 'result': {
      const state = annualSnapshot(30), push = smooth(clock.progress('result', 'close-start'));
      return {...state, camera: groundCamera(MINT.scale + .04 * push), time: clock.frame / clock.fps};
    }
    case 'closing': return closingFrame(clock);
  }
}
