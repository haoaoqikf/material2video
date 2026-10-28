/**
 * 片名卡：暗场上的金字与放射细线，母题图形由调用方传入。
 *
 * 从场景进片名是「压暗」：先在 0.55s 内暗到底，金线从暗里浮出来。
 * 全程只由帧号推进，不使用计时器或渐变 CSS 动画。
 */
import type {ReactNode} from 'react';
import {useId} from 'react';
import {T, alpha, color, frameProgress} from './kit';

export type TitleFableProps = {
  text: string;
  subtitle?: string;
  width: number;
  height: number;
  frame: number;
  startFrame?: number;
  darkenFrames?: number;
  revealFrames?: number;
  /** 母题图形：以画布中心为原点的 SVG 内容。 */
  motif?: ReactNode;
  role?: string;
  state?: string;
};

export default function TitleFable({
  text, subtitle, width, height, frame, startFrame = 0,
  darkenFrames = 17, revealFrames = 40, motif, role, state,
}: TitleFableProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const darken = frameProgress(frame, startFrame, darkenFrames);
  const reveal = frameProgress(frame, startFrame + darkenFrames, revealFrames);
  const gold = color('gold');
  const rays = Array.from({length: 48}, (_, index) => index);
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', inset: 0, width, height, pointerEvents: 'none',
      background: `rgba(7,4,1,${(0.92 * darken).toFixed(4)})`,
    }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id={`${uid}-glow`} gradientUnits="userSpaceOnUse" cx={width / 2} cy={height * 0.46}
            r={Math.max(width, height) * 0.3}>
            <stop offset="0" stopColor={gold} stopOpacity={0.2 * reveal}/>
            <stop offset="1" stopColor={gold} stopOpacity="0"/>
          </radialGradient>
        </defs>
        <rect width={width} height={height} fill={`url(#${uid}-glow)`}/>
        <g opacity={reveal * 0.34} stroke={gold} strokeWidth={1.4}>
          {rays.map(index => {
            const angle = (index / rays.length) * Math.PI * 2;
            const inner = Math.min(width, height) * 0.16;
            const outer = inner + Math.min(width, height) * (0.12 + (index % 3) * 0.035);
            const cx = width / 2;
            const cy = height * 0.46;
            return (
              <line key={index}
                x1={cx + Math.cos(angle) * inner} y1={cy + Math.sin(angle) * inner}
                x2={cx + Math.cos(angle) * outer} y2={cy + Math.sin(angle) * outer}/>
            );
          })}
        </g>
      </svg>
      {motif ? (
        <div style={{position: 'absolute', left: '50%', top: '46%', transform: 'translate(-50%, -50%)', opacity: reveal}}>
          {motif}
        </div>
      ) : null}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: '46%', transform: 'translateY(-50%)',
        textAlign: 'center', opacity: reveal,
        fontFamily: T.type.fontStack, fontSize: T.type.title, fontWeight: 700,
        letterSpacing: '0.18em', color: gold,
        textShadow: `0 0 28px ${alpha(gold, 0.5)}`,
      }}>{text}</div>
      {subtitle ? (
        <div style={{
          position: 'absolute', left: 0, right: 0, top: 'calc(46% + 96px)', textAlign: 'center',
          opacity: reveal, fontFamily: T.type.fontStack, fontSize: 40, letterSpacing: '0.2em',
          color: alpha(gold, 0.72),
        }}>{subtitle}</div>
      ) : null}
    </div>
  );
}
