/** 本轮静态选案的纯状态：真实单位、对象身份、三维堆叠与同尺度正交相机。 */
import {discFractions, secondYear, yearState, UNITS_PER_DISC} from './compoundMath';
import {CAPITAL_STYLE} from './capital-style';

export type Tone = 'white' | 'gold' | 'dark';
export type Token = {
  id: string; x: number; y: number; z: number; units: number;
  tone: Tone; opacity: number; tilt: number; gold: number;
  pitch?: number; thickness?: number;
};
export type Camera = {x: number; y: number; scale: number; elevation?: number};
export type CapitalFrame = {tokens: Token[]; camera: Camera; phase: 'opening' | 'core' | 'result'; time: number};
const token = (id: string, x: number, y: number, units = 1, tone: Tone = 'white'): Token =>
  ({id, x, y, units, tone, z: 0, opacity: 1, tilt: 0, gold: tone === 'gold' ? 1 : 0});

/** 三幅静态设计只用于图片选案，不能将切换图片的编码容器当作正式运动。 */
export function designFrame(panel: number): CapitalFrame {
  if (!Number.isInteger(panel) || panel < 0 || panel > 2) throw new Error('设计样图索引必须为0、1或2');
  const flat = (id: string, x: number, y: number, z: number, units = 1, tone: Tone = 'white') =>
    ({...token(id, x, 1080 - y, units, tone), z, pitch: -Math.PI / 2, tilt: 0, thickness: CAPITAL_STYLE.thicknessScale});
  const stack = (items: {id: string; units: number; tone: Tone}[], x: number, z: number) => {
    let bottom: number = CAPITAL_STYLE.floorY;
    return items.map(item => {
      const thickness = CAPITAL_STYLE.thicknessScale * Math.max(.35, Math.sqrt(item.units));
      const coin = flat(item.id, x, bottom + CAPITAL_STYLE.backDepth * thickness, z, item.units, item.tone);
      bottom += (CAPITAL_STYLE.faceHeight + CAPITAL_STYLE.backDepth) * thickness + .15;
      return coin;
    });
  };
  const principal = (prefix: string, n: number) => Array.from({length: n}, (_, i) =>
    ({id: `${prefix}-${i}`, units: 1, tone: 'white' as Tone}));
  if (panel === 0) {
    const camera = {x: 960, y: 845, scale: 4.2, elevation: .6};
    const xAt = (x: number) => 960 + (x - 960) / camera.scale;
    return {tokens: [...stack(principal('l', 10), xAt(987), 0),
      ...stack(principal('r', 10), xAt(1446), 0)], camera, phase: 'opening', time: 0};
  }
  if (panel === 1) {
    const camera = {x: 960, y: 828, scale: 3.7, elevation: .6};
    const xAt = (x: number) => 960 + (x - 960) / camera.scale;
    const tokens: Token[] = [...stack(principal('r', 10), xAt(588), 0),
      ...stack([{id: 'r-10', units: 1, tone: 'white'}], xAt(1320), 0)];
    const at = (id: string, x: number, y: number, units: number) => ({
      ...flat(id, xAt(x), 1080 - camera.y + (540 - y) / camera.scale / Math.cos(camera.elevation), 0, units, 'gold'),
      pitch: -1.0, tilt: -.30,
    });
    const gains = secondYear();
    tokens.push(at('year-2-original', 588, 340, gains.fromPrincipal / UNITS_PER_DISC),
      at('year-2-reinvested', 1320, 340, gains.fromGain / UNITS_PER_DISC));
    return {tokens, camera, phase: 'core', time: 12};
  }
  const camera = {x: 960, y: 794.5, scale: 2.8, elevation: .65};
  const xAt = (x: number) => 960 + (x - 960) / camera.scale;
  const tokens: Token[] = [];
  for (let i = 0; i < 4; i++) tokens.push(...stack(Array.from({length: 10}, (_, j) => ({
    id: `l-${i * 10 + j}`, units: 1, tone: (i === 0 ? 'white' : 'dark') as Tone,
  })), xAt(480) + (i % 2 ? 24 : -24), Math.floor(i / 2) * 56));
  const whites = discFractions(yearState(30).offWhiteUnits);
  const golds = discFractions(yearState(30).goldUnits);
  const heights = [8, 12, 16, 12, 8, 10, 16, 21, 16, 10, 8, 10, 10, 10, 8];
  let wi = 0, gi = 0;
  heights.forEach((height, index) => {
    const topCount = index === 7 ? 2 : 1;
    const items = [
      ...Array.from({length: height - topCount}, () => ({id: `r-${wi}`, units: whites[wi++], tone: 'white' as Tone})),
      ...Array.from({length: topCount}, () => ({id: `r-${whites.length + gi}`, units: golds[gi++], tone: 'gold' as Tone})),
    ];
    tokens.push(...stack(items, xAt(1320) + (index % 5 - 2) * 44, (Math.floor(index / 5) - 1) * 56));
  });
  return {tokens, camera, phase: 'result', time: 23};
}
