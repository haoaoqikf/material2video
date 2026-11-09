import {describe, expect, it} from 'vitest';
import {annualSnapshot, coreFrame, EVENT_FRAMES, filmClock, growthFrame} from './capital-motion';
import {yearState} from './compoundMath';
import {CAPITAL_STYLE} from './capital-style';

describe('实体资本的完整动作', () => {
  it('去年收益的同一身份归队后产生0.1单位新收益', () => {
    const before = coreFrame(filmClock(EVENT_FRAMES['rejoin-start']));
    const joined = coreFrame(filmClock(EVENT_FRAMES['rejoin-contact']));
    expect(before.tokens.find(item => item.id === 'r-10')?.gold).toBe(1);
    expect(joined.tokens.find(item => item.id === 'r-10')?.gold).toBe(0);
    expect(joined.tokens.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(11);
    const end = coreFrame(filmClock(EVENT_FRAMES['second-formed']));
    expect(end.tokens.find(item => item.id === 'gain-2-from-first')?.units).toBeCloseTo(.1);
    expect(end.tokens.find(item => item.id === 'gain-2-from-principal')?.units).toBeCloseTo(1);
    expect(end.tokens.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(12.1);
  });
  it('每年精确守恒，尾数不丢弃，最终为159白对象16金对象', () => {
    for (let year = 1; year <= 30; year++) {
      const state = annualSnapshot(year);
      const right = state.tokens.filter(item => !item.id.startsWith('l-'));
      const left = state.tokens.filter(item => item.id.startsWith('l-'));
      expect(Math.max(...right.map(item => item.z))).toBe(Math.max(...left.map(item => item.z)));
      expect(right.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(yearState(year).totalUnits);
      expect(state.tokens.filter(item => item.id.startsWith('l-')).length).toBe(10 + year);
    }
    const final = annualSnapshot(30).tokens.filter(item => !item.id.startsWith('l-'));
    expect(final.filter(item => item.gold === 0)).toHaveLength(159);
    expect(final.filter(item => item.gold === 1)).toHaveLength(16);
  });
  it('年度运动不超发、不倒退，乱序取帧与缺失事件明确处理', () => {
    for (let year = 4; year <= 30; year++) {
      const start = EVENT_FRAMES[`year-${year}`];
      const end = EVENT_FRAMES[year === 30 ? 'result' : `year-${year+1}`];
      let previous = yearState(year - 1).totalUnits;
      for (let k = 0; k <= 10; k++) {
        const frame = start + (end - start) * k / 10;
        const state = growthFrame(filmClock(frame));
        const amount = state.tokens.filter(item => !item.id.startsWith('l-')).reduce((sum, item) => sum + item.units, 0);
        expect(amount).toBeGreaterThanOrEqual(previous - 1e-7);
        expect(amount).toBeLessThanOrEqual(yearState(year).totalUnits + 1e-7);
        previous = amount;
        expect(state).toEqual(growthFrame(filmClock(frame)));
      }
    }
    const a = growthFrame(filmClock(620));
    growthFrame(filmClock(555));
    expect(growthFrame(filmClock(620))).toEqual(a);
    expect(() => growthFrame(filmClock(620, 30, {}))).toThrow('分镜事件缺失');
    expect(() => filmClock(0, 30, {a: 1, b: 1}).progress('a', 'b')).toThrow('窗口必须正向');
  });
  it('每列旧收益全部到账、父资本完整后才产生下一轮收益，所有中间帧守恒', () => {
    for (let year = 4; year <= 30; year++) {
      const previous = annualSnapshot(year - 1), target = annualSnapshot(year);
      const oldGains = previous.tokens.filter(item => item.id.startsWith('gain-'));
      const start = EVENT_FRAMES[`year-${year}`], end = EVENT_FRAMES[year === 30 ? 'result' : `year-${year + 1}`];
      for (let step = 0; step <= 100; step++) {
        const state = growthFrame(filmClock(start + (end - start) * step / 100));
        const whites = state.tokens.filter(item => item.id.startsWith('r-'));
        const remaining = state.tokens.filter(item => oldGains.some(old => old.id === item.id));
        const capital = whites.reduce((sum, item) => sum + item.units, 0);
        expect(capital + remaining.reduce((sum, item) => sum + item.units, 0))
          .toBeCloseTo(yearState(year - 1).totalUnits, 7);
        const gains = state.tokens.filter(item => item.id.startsWith(`gain-${year}-`));
        expect(gains.reduce((sum, item) => sum + item.units, 0)).toBeLessThanOrEqual(capital * .1 + 1e-7);
        for (const gain of gains) {
          expect(remaining.some(item => item.column === gain.column)).toBe(false);
          const currentColumn = whites.filter(item => item.column === gain.column).reduce((s, item) => s + item.units, 0);
          const targetColumn = target.tokens.filter(item => item.id.startsWith('r-') && item.column === gain.column)
            .reduce((s, item) => s + item.units, 0);
          expect(currentColumn).toBeCloseTo(targetColumn, 7);
        }
      }
    }
  });
  it('慢速首轮保留真实白色停顿，增长中的同列实体包括双金顶始终不互穿', () => {
    const whiteOnly: number[] = [];
    const year3Capital = annualSnapshot(3).tokens.filter(item => item.id.startsWith('r-')).reduce((s, t) => s + t.units, 0);
    for (let frame = EVENT_FRAMES['year-4']; frame < EVENT_FRAMES['year-5']; frame++) {
      const tokens = growthFrame(filmClock(frame)).tokens;
      if (!tokens.some(t => t.id === 'gain-3-0' || t.id === 'gain-4-0')
          && tokens.filter(t => t.id.startsWith('r-')).reduce((s, t) => s + t.units, 0) >= year3Capital + 1 - 1e-7) whiteOnly.push(frame);
    }
    expect(whiteOnly.some((frame, i) => whiteOnly[i + 2] === frame + 2)).toBe(true);
    const thickness = (units: number) => CAPITAL_STYLE.thicknessScale * Math.max(.35, Math.sqrt(units));
    for (let frame = EVENT_FRAMES['growth-start']; frame <= EVENT_FRAMES.result; frame += .25) {
      const tokens = growthFrame(filmClock(frame)).tokens.filter(t => !t.id.startsWith('l-'));
      const columns = new Map<number, typeof tokens>();
      for (const item of tokens) {const group = columns.get(item.column!) ?? []; group.push(item); columns.set(item.column!, group);}
      for (const group of columns.values()) {
        group.sort((a, b) => b.y - a.y);
        for (let i = 1; i < group.length; i++) {
          const lower = group[i - 1], upper = group[i];
          const gap = lower.y - upper.y - CAPITAL_STYLE.faceHeight * thickness(lower.units)
            - CAPITAL_STYLE.backDepth * thickness(upper.units);
          expect(gap, `f${frame} ${lower.id}/${upper.id}`).toBeGreaterThanOrEqual(-1e-7);
        }
      }
    }
  });
});
