/** 方案C的纯帧状态；分镜事件是动作与声音的共同时间来源。 */
import storyboard from '../storyboard.json';
import {easeMotion} from '../src/code-scene/motion';
import {clamp, discFractions, yearState} from './compoundMath';
import {designFrame} from './capital-state';
import type {CapitalFrame, Token} from './capital-state';
import {CAPITAL_STYLE, RESULT_LAYOUT} from './capital-style';
import {DIRECTIONS, directionFrame} from './typography-themes';

export const MINT = DIRECTIONS[2];
export const FILM_DURATION_FRAMES = storyboard.scenes[0].durationFrames;
export const EVENT_FRAMES: Readonly<Record<string, number>> = Object.fromEntries(
  storyboard.scenes[0].events.map(({id, frame}) => [id, frame]));
export type FilmClock = {frame: number; fps: number; at: (id: string) => number;
  progress: (start: string, end: string) => number; passed: (id: string) => boolean;
  atFrame: (frame: number) => FilmClock};
export function filmClock(frame: number, fps = 30, events = EVENT_FRAMES): FilmClock {
  if (!Number.isFinite(frame) || !Number.isFinite(fps) || fps <= 0) throw new Error('无效帧时钟');
  const at = (id: string) => {
    const value = events[id];
    if (!Number.isFinite(value)) throw new Error(`分镜事件缺失：${id}`);
    return value;
  };
  const progress = (start: string, end: string) => {
    const first = at(start), last = at(end);
    if (last <= first) throw new Error(`分镜事件窗口必须正向：${start} → ${end}`);
    return clamp((frame - first) / (last - first));
  };
  return {frame, fps, at, progress, passed: (id: string) => frame >= at(id),
    atFrame: next => filmClock(next, fps, events)};
}
const out = (p: number) => easeMotion('easeOutCubic', clamp(p));
const smooth = (p: number) => easeMotion('easeInOutCubic', clamp(p));
const mix = (a: number, b: number, p: number) => a + (b - a) * p;
export function moveCoin(a: Token, b: Token, p: number): Token {
  return {...b, x: mix(a.x, b.x, p), y: mix(a.y, b.y, p), z: mix(a.z, b.z, p),
    pitch: mix(a.pitch ?? 0, b.pitch ?? 0, p), tilt: mix(a.tilt, b.tilt, p),
    units: mix(a.units, b.units, p), gold: mix(a.gold, b.gold, p), opacity: mix(a.opacity, b.opacity, p)};
}
const mint = (state: CapitalFrame): CapitalFrame => ({...state,
  palette: {background: MINT.background, floor: MINT.floor}});
const thickness = (units: number) => CAPITAL_STYLE.thicknessScale * Math.max(.35, Math.sqrt(units));
const top = (coin: Token) => 1080 - coin.y + CAPITAL_STYLE.faceHeight * thickness(coin.units) + .15;
const flat = (id: string, x: number, bottom: number, z: number, units: number, gold = 0): Token =>
  ({id, x, y: 1080 - bottom - CAPITAL_STYLE.backDepth * thickness(units), z, units,
    tone: gold ? 'gold' : 'white', gold, opacity: 1, pitch: -Math.PI / 2, tilt: 0,
    thickness: CAPITAL_STYLE.thicknessScale});

/** 先看一枚去年收益归队变白，再从对应父对象生长两种面积的新收益。 */
export function coreFrame(clock: FilmClock): CapitalFrame {
  const base = mint(designFrame(1));
  const join = smooth(clock.progress('rejoin-start', 'rejoin-contact'));
  const original = base.tokens.slice(0, 10);
  const principalX = original[0].x;
  const centerX = 960;
  const gain = base.tokens[10];
  const previous = {...gain, x: centerX, y: gain.y - 92, gold: 1,
    tone: 'gold' as const, pitch: -1.0, tilt: -.3};
  const prior = moveCoin(previous, gain, join);
  prior.y -= 35 * Math.sin(Math.PI * join);
  const birth = out(clock.progress('second-birth', 'second-formed'));
  const tokens = [...original.map(item => ({...item, x: item.x + (centerX - principalX) * (1 - join)})), prior];
  if (birth > 0) for (let i = 0; i < 2; i++) {
    const target = base.tokens[11 + i];
    const parent = i === 0 ? original[9] : gain;
    const source = {...target, x: parent.x, y: 1080 - top(parent), units: 0,
      pitch: -Math.PI / 2, tilt: 0, opacity: 0};
    tokens.push({...moveCoin(source, target, birth), id: i ? 'gain-2-from-first' : 'gain-2-from-principal'});
  }
  return {...base, tokens, time: clock.frame / clock.fps};
}

const result = directionFrame(2);
const resultWhite = result.tokens.filter(item => item.id.startsWith('r-') && item.tone === 'white');
/** 每年白色资本用稳定桶身份，收益在已有资本表面生成；尾数始终按真实面积保留。 */
export function annualSnapshot(year: number): CapitalFrame {
  if (!Number.isInteger(year) || year < 1 || year > 30) throw new Error('年度快照必须为1到30');
  const value = yearState(year);
  const whites = discFractions(value.offWhiteUnits, 0).filter(unit => unit > 1e-8);
  const right = whites.map((units, i) => ({...resultWhite[i], units,
    y: resultWhite[i].y + CAPITAL_STYLE.backDepth * (thickness(resultWhite[i].units) - thickness(units))}));
  const columns = new Map<string, Token[]>();
  for (const item of right) {
    const key = `${item.x}:${item.z}`;
    const values = columns.get(key) ?? [];
    item.column = columns.has(key) ? values[0].column : columns.size;
    values.push(item); columns.set(key, values);
  }
  const stacks = [...columns.values()];
  const golds = discFractions(value.goldUnits, 0).filter(unit => unit > 1e-8);
  golds.forEach((units, i) => {
    const column = stacks[i < stacks.length ? i : 7 % stacks.length];
    const parent = column[column.length - 1];
    const id = year === 2 ? (i ? 'gain-2-from-first' : 'gain-2-from-principal') : `gain-${year}-${i}`;
    const coin = flat(id, parent.x, top(parent), parent.z, units, 1);
    coin.column = parent.column;
    right.push(coin); column.push(coin);
  });
  // 小额阶段只占少数列，居中排列；第30年保持已选C样图原构图。
  const minX = Math.min(...right.map(item => item.x));
  const maxX = Math.max(...right.map(item => item.x));
  const finalCenter = 960 + (MINT.right - 960) / MINT.scale;
  const dx = finalCenter - (minX + maxX) / 2;
  right.forEach(item => {item.x += dx;});
  const left = result.tokens.filter(item => item.id.startsWith('l-'))
    .filter(item => item.tone === 'white' || Number(item.id.slice(2)) < 10 + year)
    .map(item => ({...item}));
  for (const group of [left, right]) {
    const dz = RESULT_LAYOUT.rowDepth - Math.max(...group.map(item => item.z));
    group.forEach(item => {item.z += dz;});
  }
  return {...result, tokens: [...left, ...right], time: year};
}

function leftTransition(previous: CapitalFrame, target: CapitalFrame, birth: number, layout: number) {
  const oldLeft = new Map(previous.tokens.filter(item => item.id.startsWith('l-')).map(item => [item.id, item]));
  return target.tokens.filter(item => item.id.startsWith('l-')).map(item => {
    const old = oldLeft.get(item.id);
    if (old) return moveCoin(old, item, layout);
    const source = target.tokens.find(item => item.id === 'l-9')!;
    const moved = moveCoin({...source, units: 0, opacity: 0, gold: 1, tone: 'gold'}, item, birth);
    moved.y -= 25 * Math.sin(Math.PI * birth);
    return moved;
  });
}

/** 分流镜头使用分镜中两个独立的归队/生息窗口。 */
export function transitionYear(year: number, commitProgress: number, birthProgress: number,
  withdrawProgress = birthProgress, layoutProgress = commitProgress): CapitalFrame {
  const previous = annualSnapshot(year - 1), target = annualSnapshot(year);
  // 原本金始终在生息；其新收益与其他旧收益的归队错开重叠，避免快进时整排先白后金闪烁。
  const commit = smooth(commitProgress), birth = out(birthProgress), withdraw = out(withdrawProgress);
  const layout = smooth(layoutProgress);
  const oldRight = previous.tokens.filter(item => item.id.startsWith('r-'));
  const oldGains = previous.tokens.filter(item => item.id.startsWith('gain-'));
  const targets = target.tokens.filter(item => item.id.startsWith('r-'));
  const oldMap = new Map(oldRight.map(item => [item.id, item]));
  const tokens: Token[] = targets.map((item, i) => {
    const old = oldMap.get(item.id);
    const source = old ?? {...oldGains[Math.min(oldGains.length - 1, Math.max(0, i - oldRight.length))],
      units: 0, opacity: 1};
    return {...moveCoin(source, item, commit), id: item.id,
      x: mix(source.x, item.x, layout), y: mix(source.y, item.y, layout), z: mix(source.z, item.z, layout)};
  });
  oldGains.forEach((item, i) => {
    if (commit >= 1) return;
    const targetCoin = targets[Math.min(targets.length - 1, oldRight.length + i)];
    const moved = moveCoin(item, {...targetCoin, gold: 0, units: item.units}, layout);
    tokens.push({...moved, id: item.id, gold: 1 - commit, units: item.units * (1 - commit)});
  });
  target.tokens.filter(item => item.id.startsWith('gain-')).forEach(item => {
    if (birth <= 0) return;
    const targetParent = targets.filter(coin => coin.x === item.x && coin.z === item.z).at(-1)!;
    const parent = tokens.find(coin => coin.id === targetParent.id)!;
    const from = {...item, y: 1080 - top(parent), units: 0, opacity: 0};
    const coin = moveCoin(from, item, birth);
    coin.y -= 22 * Math.sin(Math.PI * birth);
    tokens.push(coin);
  });
  tokens.push(...leftTransition(previous, target, withdraw, layout));
  return {...target, tokens: tokens.filter(item => item.units > 1e-8)};
}

// 每列先把旧收益完整转白，保留白色窗口，再生成新收益；列间错开以避免整排金顶同时清空。
const columnOffset = (column: number) => (column % 3) * .28;
const committed = (column: number, progress: number) => smooth((progress - columnOffset(column)) / .18);
const fundingThresholds = new Map<string, number>();
function fundedAt(year: number, column: number, prefix: number, previousWhite: number, gains: Token[]) {
  const key = `${year}:${column}`;
  const cached = fundingThresholds.get(key);
  if (cached !== undefined) return cached;
  let lo = 0, hi = 1;
  const capitalAt = (p: number) => previousWhite + gains.reduce((sum, item) =>
    sum + item.units * committed(item.column!, p), 0);
  if (capitalAt(0) >= prefix - 1e-9) hi = 0;
  else for (let i = 0; i < 36; i++) {
    const middle = (lo + hi) / 2;
    if (capitalAt(middle) >= prefix - 1e-9) hi = middle; else lo = middle;
  }
  // 仅缓存由固定数学模型决定的数字阈值，不缓存任何可变帧状态。
  fundingThresholds.set(key, hi);
  return hi;
}

function waveYear(year: number, progress: number, birthStart: number, birthSpan: number): CapitalFrame {
  const previous = annualSnapshot(year - 1), target = annualSnapshot(year);
  const oldWhite = previous.tokens.filter(item => item.id.startsWith('r-'));
  const oldGains = previous.tokens.filter(item => item.id.startsWith('gain-'));
  const whites = target.tokens.filter(item => item.id.startsWith('r-'));
  const previousWhite = oldWhite.reduce((sum, item) => sum + item.units, 0);
  const capital = previousWhite + oldGains.reduce((sum, item) =>
    sum + item.units * committed(item.column!, progress), 0);
  const layout = smooth(progress);
  const dx = (oldWhite[0].x - whites[0].x) * (1 - layout);
  const dz = (oldWhite[0].z - whites[0].z) * (1 - layout);
  const tops = new Map<number, Token>();
  const tokens: Token[] = [];
  // 资本按稳定桶连续到账，每列从地面向上重建实际厚度，分数生长不压进下层。
  whites.forEach((item, i) => {
    const units = clamp(capital - i);
    if (units <= 1e-8) return;
    const below = tops.get(item.column!);
    const coin = {...flat(item.id, item.x + dx, below ? top(below) : CAPITAL_STYLE.floorY,
      item.z + dz, units), column: item.column};
    tokens.push(coin); tops.set(item.column!, coin);
  });
  const remainingTops = new Map(tops);
  for (const item of oldGains) {
    const commit = committed(item.column!, progress), units = item.units * (1 - commit);
    if (units <= 1e-8) continue;
    const below = remainingTops.get(item.column!)!;
    const coin = {...flat(item.id, below.x, top(below), below.z, units, 1 - commit), column: item.column};
    tokens.push(coin); remainingTops.set(item.column!, coin);
  }
  const newTops = new Map(tops);
  const parentIndices = new Map<number, number>();
  whites.forEach((item, i) => parentIndices.set(item.column!, i));
  for (const item of target.tokens.filter(coin => coin.id.startsWith('gain-'))) {
    const column = item.column!;
    const parentIndex = parentIndices.get(column)!;
    const prefix = parentIndex + whites[parentIndex].units;
    const start = Math.max(columnOffset(column) + birthStart,
      fundedAt(year, column, prefix, previousWhite, oldGains) + .1);
    const birth = out((progress - start) / birthSpan);
    if (birth <= 0) continue;
    const below = newTops.get(column)!;
    // 同列第二枚收益站在已生成的第一枚上；始终跟随真实父体，不能从未来空列生长或互穿。
    const coin = {...flat(item.id, below.x, top(below), below.z, item.units * birth, 1), column};
    tokens.push(coin); newTops.set(column, coin);
  }
  tokens.push(...leftTransition(previous, target, out(progress), layout));
  return {...target, tokens: tokens.filter(item => item.units > 1e-8)};
}
export function growthYear(clock: FilmClock) {
  let year = 3;
  for (let n = 4; n <= 30; n++) if (clock.passed(`year-${n}`)) year = n;
  return year;
}
export function growthFrame(clock: FilmClock): CapitalFrame {
  const year = growthYear(clock);
  if (year === 3) return annualSnapshot(3);
  const next = year === 30 ? 'result' : `year-${year + 1}`;
  const progress = clock.progress(`year-${year}`, next);
  const firstCycle = clock.at('year-5') - clock.at('year-4');
  const birthStart = (clock.at('growth-first-birth') - clock.at('year-4')) / firstCycle;
  const birthSpan = (clock.at('growth-first-formed') - clock.at('growth-first-birth')) / firstCycle;
  return {...waveYear(year, progress, birthStart, birthSpan), time: clock.frame / clock.fps};
}
