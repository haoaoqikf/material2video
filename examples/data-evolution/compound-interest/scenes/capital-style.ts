import {FULL_DIAMETER} from './compoundMath';

/** 堆叠与实际网格共用边界，避免视图几何和模型的接触零点各维护一份。 */
export const CAPITAL_STYLE = {
  radius: FULL_DIAMETER / 2,
  floorY: 180,
  backDepth: 4.5,
  faceHeight: 7.4,
  thicknessScale: .42,
} as const;
