import { describe, expect, it } from 'vitest';
import { OPENING_DURATIONS, resolveDesign, withAlpha } from './design';

describe('金融设计档案', () => {
  it('缺省使用 signal/subject/corporate 且无 accent', () => {
    const design = resolveDesign(undefined);
    expect(design.profile).toBe('signal');
    expect(design.titleMode).toBe('subject');
    expect(design.personality).toBe('corporate');
    expect(design.accent).toBeNull();
  });

  it('接受三种 profile 与可选 accent，accent 覆盖 profile tint', () => {
    const ledger = resolveDesign({profile: 'ledger', accent: '#C9A45C'});
    expect(ledger.glow).toBe('#1A1713');
    expect(ledger.tint).toBe('#C9A45C');
    const archive = resolveDesign({profile: 'archive'});
    expect(archive.tint).toBe('#6F8CA8');
  });

  it('拒绝未知枚举、非法 accent 与涨跌颜色', () => {
    expect(() => resolveDesign({profile: 'unknown' as never})).toThrow('profile');
    expect(() => resolveDesign({titleMode: 'other' as never})).toThrow('标题模式');
    expect(() => resolveDesign({personality: 'other' as never})).toThrow('运动人格');
    expect(() => resolveDesign({accent: '#FFF'})).toThrow('#RRGGBB');
    expect(() => resolveDesign({accent: '#FF5A4E'})).toThrow('正收益');
    expect(() => resolveDesign({accent: '#4bd39a'})).toThrow('负收益');
  });

  it('withAlpha 输出 rgba 并拒绝非法颜色', () => {
    expect(withAlpha('#C9A45C', 0.045)).toBe('rgba(201, 164, 92, 0.045)');
    expect(() => withAlpha('red', 0.1)).toThrow('#RRGGBB');
  });

  it('运动人格只改变开场时长，不改变数据时间', () => {
    expect(OPENING_DURATIONS.corporate.chart).toBe(12);
    expect(OPENING_DURATIONS.premium.chart).toBe(16);
    expect(OPENING_DURATIONS.calm.chart).toBe(20);
  });
});
