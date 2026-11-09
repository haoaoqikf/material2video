import {expect, it} from 'vitest';
import storyboard from '../storyboard.json';
import {EVENT_FRAMES, filmClock} from './capital-motion';
import {fullFrame} from './mint-film-motion';
import {CAPITAL_STYLE} from './capital-style';

it('除片尾明确切镜外，各阶段相机连续，不在收益身份交接时跳变缩放', () => {
  for (const event of ['first-start', 'core-start', 'compare-start', 'growth-start', 'result']) {
    const at = EVENT_FRAMES[event];
    const before = fullFrame(filmClock(at - 1e-5)).camera;
    const after = fullFrame(filmClock(at)).camera;
    for (const key of ['x', 'y', 'scale', 'elevation'] as const) {
      expect(Math.abs((before[key] ?? 0) - (after[key] ?? 0)), `${event}:${key}`).toBeLessThan(.001);
    }
  }
});

it('片尾同列圆片在全部子帧保持原来的上下关系且不穿插', () => {
  const initial = fullFrame(filmClock(EVENT_FRAMES['close-start'])).tokens;
  const columns = new Map<string, typeof initial>();
  for (const item of initial) {
    const key = `${item.x}:${item.z}`;
    const group = columns.get(key) ?? []; group.push(item); columns.set(key, group);
  }
  for (const group of columns.values()) group.sort((a, b) => b.y - a.y);
  for (let frame = EVENT_FRAMES['close-start']; frame <= EVENT_FRAMES['close-return']; frame += .25) {
    const current = new Map(fullFrame(filmClock(frame)).tokens.map(item => [item.id, item]));
    for (const group of columns.values()) for (let i = 1; i < group.length; i++) {
      const below = current.get(group[i - 1].id)!, above = current.get(group[i].id)!;
      const thickness = (units: number) => CAPITAL_STYLE.thicknessScale * Math.max(.35, Math.sqrt(units));
      const lowerTop = 1080 - below.y + CAPITAL_STYLE.faceHeight * thickness(below.units);
      const upperBottom = 1080 - above.y - CAPITAL_STYLE.backDepth * thickness(above.units);
      const originalGap = (1080 - group[i].y - CAPITAL_STYLE.backDepth * thickness(group[i].units))
        - (1080 - group[i - 1].y + CAPITAL_STYLE.faceHeight * thickness(group[i - 1].units));
      expect(upperBottom - lowerTop, `f${frame}: ${below.id} / ${above.id}`)
        .toBeGreaterThanOrEqual(Math.max(0, originalGap) - 1e-7);
    }
  }
});

it('第一年收益身份跨镜头保持，开场两组本金等量', () => {
  const opening = fullFrame(filmClock(100));
  for (const prefix of ['l-', 'r-']) expect(opening.tokens.filter(item => item.id.startsWith(prefix))
    .reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(10);
  const first = fullFrame(filmClock(EVENT_FRAMES['first-formed']));
  const core = fullFrame(filmClock(EVENT_FRAMES['rejoin-contact']));
  expect(first.tokens.find(item => item.id === 'r-10')?.gold).toBe(1);
  expect(core.tokens.find(item => item.id === 'r-10')?.gold).toBe(0);
  expect(core.tokens.find(item => item.id === 'r-10')?.units).toBe(1);
});

it('两路第2年收益同步分流，第三年规模依余额生长', () => {
  const start = fullFrame(filmClock(EVENT_FRAMES['split-start']));
  const end = fullFrame(filmClock(EVENT_FRAMES['split-contact']));
  expect(start.tokens.find(item => item.id === 'l-11')?.gold).toBe(1);
  expect(end.tokens.find(item => item.id === 'l-11')?.gold).toBe(0);
  const right = end.tokens.filter(item => !item.id.startsWith('l-'));
  expect(right.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(12.1);
  expect(right.every(item => item.gold === 0)).toBe(true);
  const next = fullFrame(filmClock(EVENT_FRAMES['third-contact']));
  expect(next.tokens.filter(item => item.id.startsWith('l-')).reduce((s, item) => s + item.units, 0)).toBeCloseTo(13);
  expect(next.tokens.filter(item => !item.id.startsWith('l-')).reduce((s, item) => s + item.units, 0)).toBeCloseTo(13.31);
});

it('片尾16金逐个归队，175个对象与174.494单位守恒且最终全白', () => {
  const before = fullFrame(filmClock(EVENT_FRAMES['close-start']));
  const final = fullFrame(filmClock(869));
  expect(before.tokens).toHaveLength(175);
  expect(before.tokens.filter(item => item.gold === 1)).toHaveLength(16);
  expect(final.tokens).toHaveLength(175);
  expect(final.tokens.every(item => item.gold === 0 && item.tone === 'white')).toBe(true);
  expect(final.tokens.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(174.4940226888645);
  expect(final.tokens.map(item => [item.id, item.units])).toEqual(before.tokens.map(item => [item.id, item.units]));
});

it('完整870帧有限、无重复身份、乱序确定，所有事件声共用分镜事件', () => {
  for (let frame = 0; frame < 870; frame++) {
    const state = fullFrame(filmClock(frame));
    expect(new Set(state.tokens.map(item => item.id)).size).toBe(state.tokens.length);
    expect(Object.values(state.camera).every(Number.isFinite)).toBe(true);
    expect(state.tokens.every(item => [item.x, item.y, item.z, item.units, item.gold, item.opacity].every(Number.isFinite))).toBe(true);
    expect(state.tokens.every(item => item.units > 0 && item.units <= 1 + 1e-8)).toBe(true);
  }
  const sample = fullFrame(filmClock(770));
  fullFrame(filmClock(30));
  expect(fullFrame(filmClock(770))).toEqual(sample);
  for (const effect of storyboard.soundtrack.effects) {
    expect(Number.isInteger(EVENT_FRAMES[effect.eventId])).toBe(true);
    expect('offsetFrames' in effect).toBe(false);
  }
});
