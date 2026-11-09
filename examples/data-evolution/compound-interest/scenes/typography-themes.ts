import {designFrame} from './capital-state';
import type {CapitalFrame} from './capital-state';
import {CAPITAL_STYLE, RESULT_LAYOUT} from './capital-style';

export const DIRECTIONS = [
  {id: 'paper', name: '暖纸编辑', background: '#efe6d7', floor: '#efe2cc', ink: '#4b292a',
    muted: '#765f5b', chinese: 'M2V XiaoWei', numbers: 'M2V DM Serif', scale: 2.25, left: 480, right: 1340, base: 850},
  {id: 'violet', name: '浅紫海报', background: '#e6dff6', floor: '#d8cbea', ink: '#302142',
    muted: '#675870', chinese: 'M2V QingKe', numbers: 'M2V Bebas', scale: 2, left: 760, right: 1430, base: 880},
  {id: 'mint', name: '薄荷人文', background: '#dce9dc', floor: '#c7ddcc', ink: '#254a3a',
    muted: '#557263', chinese: 'M2V ShanZheng', numbers: 'M2V Fraunces', scale: 2, left: 480, right: 1360, base: 880},
] as const;

/** 数据和圆片完整复用同一终态，改变的是排版构图和现场，不更改单位与两组尺度。 */
export function directionFrame(index: number): CapitalFrame {
  const direction = DIRECTIONS[index];
  if (!direction) throw new Error('未知字体方向');
  const original = designFrame(2);
  const elevation = original.camera.elevation!;
  const focusY = CAPITAL_STYLE.floorY + ((direction.base - 540) / direction.scale
    - RESULT_LAYOUT.rowDepth * Math.sin(elevation)) / Math.cos(elevation);
  return {...original,
    palette: {background: direction.background, floor: direction.floor},
    camera: {...original.camera, scale: direction.scale, y: 1080 - focusY},
    tokens: original.tokens.map(item => {
      const from = item.id.startsWith('l-') ? RESULT_LAYOUT.left : RESULT_LAYOUT.right;
      const to = item.id.startsWith('l-') ? direction.left : direction.right;
      const oldCenter = 960 + (from - 960) / original.camera.scale;
      const center = 960 + (to - 960) / direction.scale;
      return {...item, x: item.x - oldCenter + center};
    }),
  };
}
