/**
 * 页面边界的单一金色交接物：不是粒子场，只在一个边界前后出现。
 * 位置来自设计表；形状只区分点/水滴/金片/谷粒/环。
 */
import {T} from 'm2v/style/components/kit';

const GOLD = T.colors.gold;

type Kind = 'dot' | 'drop' | 'shard' | 'grain' | 'ring';

type Handoff = {
  at: number;
  from: {x: number; y: number};
  to: {x: number; y: number};
  kind: Kind;
};

export const HANDOFFS: Handoff[] = [
  {at: 180, from: {x: 1080, y: 500}, to: {x: 960, y: 240}, kind: 'drop'},
  {at: 420, from: {x: 1400, y: 300}, to: {x: 520, y: 400}, kind: 'grain'},
  {at: 600, from: {x: 1150, y: 560}, to: {x: 1160, y: 660}, kind: 'shard'},
  {at: 720, from: {x: 760, y: 660}, to: {x: 960, y: 520}, kind: 'dot'},
  {at: 900, from: {x: 960, y: 140}, to: {x: 975, y: 820}, kind: 'shard'},
  {at: 1080, from: {x: 1440, y: 240}, to: {x: 1160, y: 240}, kind: 'dot'},
  // 1230 是唯一硬切：不插值、不画交接物。
  {at: 1410, from: {x: 1270, y: 470}, to: {x: 715, y: 275}, kind: 'grain'},
  {at: 1560, from: {x: 1205, y: 725}, to: {x: 960, y: 160}, kind: 'grain'},
];

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function easeInOutSine(t: number): number {
  return -(Math.cos(Math.PI * clamp01(t)) - 1) / 2;
}

export function HandoffLayer({frame}: {frame: number}) {
  const visible = HANDOFFS.filter(handoff => Math.abs(frame - handoff.at) <= 12);
  return (
    <svg width={1920} height={1080} viewBox="0 0 1920 1080"
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}}
      aria-hidden>
      {visible.map(handoff => {
        const t = easeInOutSine((frame - (handoff.at - 10)) / 20);
        const x = handoff.from.x + (handoff.to.x - handoff.from.x) * t;
        const y = handoff.from.y + (handoff.to.y - handoff.from.y) * t;
        const fade = Math.min(1, (frame - (handoff.at - 12)) / 4,
          1 - (frame - (handoff.at + 8)) / 4);
        const opacity = Math.max(0, fade);
        if (opacity <= 0) return null;
        if (handoff.kind === 'drop') {
          return <path key={handoff.at} d={`M${x} ${y - 14} C${x + 10} ${y - 2} ${x + 9} ${y + 9} ${x} ${y + 13} C${x - 9} ${y + 9} ${x - 10} ${y - 2} ${x} ${y - 14} Z`}
            fill={GOLD} opacity={opacity * 0.9}/>;
        }
        if (handoff.kind === 'shard') {
          return <path key={handoff.at} d={`M${x - 9} ${y + 3} L${x + 7} ${y - 9} L${x + 10} ${y + 5} L${x - 3} ${y + 10} Z`}
            fill={GOLD} opacity={opacity * 0.9}/>;
        }
        if (handoff.kind === 'grain') {
          return <ellipse key={handoff.at} cx={x} cy={y} rx={5} ry={8} fill={GOLD}
            opacity={opacity * 0.9}/>;
        }
        if (handoff.kind === 'ring') {
          return <circle key={handoff.at} cx={x} cy={y} r={11} fill="none" stroke={GOLD}
            strokeWidth={2} opacity={opacity * 0.8}/>;
        }
        return <circle key={handoff.at} cx={x} cy={y} r={6} fill={GOLD} opacity={opacity * 0.9}/>;
      })}
    </svg>
  );
}
