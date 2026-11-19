import {describe, expect, it} from 'vitest';
import {
  annualState, baseY, beats, chartScale, contribution, growAnnualBars, half, halfTotals,
  macroState, principal, rate, ratio, share, towerScale, yearly,
} from './compound-model';

describe('年度收益与双塔编码', () => {
  it('收益按上年余额递推，次年新增的利息来自首年收益', () => {
    expect(yearly[1] - yearly[0]).toBeCloseTo(contribution, 10);
    yearly.slice(1).forEach((value, index) => expect(value / yearly[index]).toBeCloseTo(1 + rate, 12));
    expect(ratio).toBeCloseTo((1 + rate) ** half, 12);
    expect(share).toBeCloseTo(1 / (1 + ratio), 12);
  });

  it('本金分层保持原高度，首年收益落在连续堆叠的本金上', () => {
    const {blocks, first, extra} = macroState(beats.reveal[1]);
    const capital = blocks.filter(block => block.glass === 'ink');
    const principalHeight = capital.reduce((height, block) => height + block.height, 0);
    expect(first.height / principalHeight).toBeCloseTo(yearly[0] / principal, 12);
    const top = capital[capital.length - 1];
    expect(first.y + first.height / 2).toBeCloseTo(top.y - top.height / 2, 12);
    const volume = (block: typeof first) => block.width * block.height * block.depth;
    const principalVolume = capital.reduce((total, block) => total + volume(block), 0);
    expect(volume(extra) / principalVolume).toBeCloseTo(contribution / principal, 12);
  });

  it('年度柱的底线共用，合塔后每块的顶端接下一块底端', () => {
    const chart = annualState(beats.assemble, 'offset');
    expect(chart.baseline).toBe(baseY);
    chart.blocks.forEach((block, index) => {
      expect(block.y + block.height / 2).toBeCloseTo(chart.baseline, 9);
      expect(block.height).toBeCloseTo(yearly[index] * chartScale, 9);
    });
    const separated = annualState(beats.assemble + 1.17, 'offset');
    expect(separated.blocks[half].x - separated.blocks[half - 1].x).toBeGreaterThan(80);
    separated.blocks.forEach(block => expect(block.y + block.height / 2).toBeCloseTo(separated.baseline, 9));
    for (const layout of ['offset', 'center'] as const) {
      const towers = annualState(beats.duration, layout);
      for (const [group, total] of halfTotals.entries()) {
        const parts = towers.blocks.slice(group * half, (group + 1) * half);
        let bottom = towers.baseline;
        for (const [index, block] of parts.entries()) {
          expect(block.y + block.height / 2).toBeCloseTo(bottom, 9);
          expect(block.height).toBeCloseTo(yearly[group * half + index] * towerScale, 9);
          bottom = block.y - block.height / 2;
        }
        expect(towers.baseline - bottom).toBeCloseTo(total * towerScale, 9);
      }
    }
  });

  it('收拢时各组保持年份顺序，且塔顶和斜投影有可见留白', () => {
    let previousScale = chartScale;
    for (let frame = 0; frame <= 90; frame++) {
      const {blocks, scale} = annualState(beats.assemble + frame / 30, 'offset');
      expect(scale).toBeLessThanOrEqual(previousScale);
      previousScale = scale;
      for (const [index, block] of blocks.entries()) {
        const projectedTop = block.y - block.height / 2 - (block.depth - (block.z ?? 0)) * 0.37;
        expect(projectedTop).toBeGreaterThan(100);
        if (index % half !== 0) expect(block.x + 1e-8).toBeGreaterThanOrEqual(blocks[index - 1].x);
      }
    }
  });

  it('生长时柱脚始终固定，未到年份为空，长满后与合塔起态一致', () => {
    const plot = annualState(beats.assemble, 'offset');
    const starts = yearly.map((_, index) => index * .12);
    const first = growAnnualBars(plot, starts, .06);
    const mid = growAnnualBars(plot, starts, .23);
    expect(first.blocks[1].height).toBe(0);
    expect(first.blocks[0].height).toBeGreaterThan(0);
    expect(mid.blocks[0].height).toBeGreaterThan(first.blocks[0].height);
    expect(mid.blocks[0].height).toBeLessThan(plot.blocks[0].height);
    for (const {blocks} of [first, mid]) {
      blocks.forEach((block, index) => {
        expect(block.y + block.height / 2).toBeCloseTo(plot.baseline, 9);
        expect(block.width).toBe(plot.blocks[index].width);
      });
    }
    expect(growAnnualBars(plot, starts, 10).blocks).toEqual(plot.blocks);
  });

  it('正式合塔从未变形的年度柱接入，两组先拉开，末片最后贴合', () => {
    const begin = annualState(beats.assemble, 'offset', true);
    const split = annualState(beats.assemble + .72, 'offset', true);
    const last = annualState(beats.assemble + 2.40, 'offset', true);
    const end = annualState(beats.assemble + 2.65, 'offset', true);
    expect(begin.blocks.map(({x}) => x)).toEqual(annualState(beats.assemble, 'offset').blocks.map(({x}) => x));
    expect(split.blocks[half].x - split.blocks[half - 1].x).toBeGreaterThan(100);
    const gap = ({blocks}: typeof begin) => {
      const lower = blocks[blocks.length - 2];
      const upper = blocks[blocks.length - 1];
      return lower.y - lower.height / 2 - upper.y - upper.height / 2;
    };
    expect(gap(last)).toBeGreaterThan(10);
    expect(gap(end)).toBeCloseTo(0, 9);
  });
});
