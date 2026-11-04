/**
 * 《接》v4：10 场、多种说明方式。
 *
 * S1 物理因果 → S2 水滴日计数 → S3 数字滚动 → S4 定义回环 → S5 数学螺旋
 * → S6 尺度/曲线 → S7 对照两堆 → S8 网络 → S9 棋盘 → S10 99/4,950。
 *
 * 没有全局粒子场；页面边界只保留一个金色交接物。唯一硬切 1230（41.0 秒）。
 */
import {useEffect, useRef, type CSSProperties, type ReactNode} from 'react';
import {beatPulse, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {MathFormula, ensureMathReady} from 'm2v/code-scene/math';
import Stage from 'm2v/style/components/stage';
import BilingualTitle from 'm2v/style/components/bilingual-title';
import ScreenSubtitle, {type SubtitleVariant} from 'm2v/style/components/screen-subtitle';
import Burst from 'm2v/style/components/burst';
import ShockRing from 'm2v/style/components/shock-ring';
import {ChartFrame, ChartLine, ChartMarker} from 'm2v/style/components/proof-chart';
import {
  LATIN, NUMERIC_STYLE, SANS, T, frameProgress, lerp,
} from 'm2v/style/components/kit';
import {
  CX, CY, H, SAMPLE, W, allChordsPath, curveValue,
  firstTenPath, lastTenPath, loopThreads, networkNodes, paperStackTop,
} from './geometry';
import {
  RollingFigure, breathe, enterPage, leavePage, sampleTimeline, textFade,
  type TimelineKey,
} from './motion';
import {HandoffLayer} from './handoff';

const IVORY = T.colors.ivory;
const GOLD = T.colors.gold;
const EMBER = T.colors.ember;
const MUTED = T.colors.muted;
const LINE = T.colors.line;

const TL: Record<string, TimelineKey[]> = {
  cut: [{start: 20, end: 116, from: 0, to: 8}],
  drops: [{start: 196, end: 400, from: 0, to: 100}],
  cuts: [{start: 426, end: 560, from: 1, to: 100}],
  loop: [{start: 612, end: 690, from: 0, to: 1}],
  turns: [{start: 750, end: 870, from: 0, to: 6}],
  folds: [{start: 916, end: 1000, from: 0, to: 42}],
  steps: [{start: 1096, end: 1210, from: 0, to: 42}],
  left: [{start: 1232, end: 1280, from: 0, to: 45}],
  right: [{start: 1232, end: 1290, from: 0, to: 945}],
  cells: [{start: 1420, end: 1545, from: 1, to: 64}],
  loop99: [{start: 1576, end: 1638, from: 0, to: 99}],
  final: [{start: 1658, end: 1740, from: 99, to: 4950}],
};

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function SvgLayer({children, style}: {children: ReactNode; style?: CSSProperties}) {
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none', ...style}}
      aria-hidden>{children}</svg>
  );
}

function Label({
  children, x, y, size = 30, color = MUTED, opacity = 1, latin = false,
  align = 'left',
}: {
  children: ReactNode; x: number; y: number; size?: number; color?: string;
  opacity?: number; latin?: boolean; align?: 'left' | 'center' | 'right';
}) {
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      transform: align === 'center' ? 'translate(-50%, -50%)'
        : align === 'right' ? 'translate(-100%, -50%)' : 'translate(0, -50%)',
      fontFamily: latin ? LATIN : SANS, fontSize: size, lineHeight: 1.3,
      color, opacity, whiteSpace: 'nowrap', letterSpacing: latin ? '0.06em' : '0.02em',
    }}>{children}</div>
  );
}

function Power({
  base, exponent, x, y, size, color = IVORY, opacity = 1, suffix, align = 'left',
}: {
  base: string; exponent: string; x: number; y: number; size: number; color?: string;
  opacity?: number; suffix?: string; align?: 'left' | 'center';
}) {
  const translate = align === 'center' ? 'translate(-50%, -50%)' : 'translate(0, -50%)';
  return (
    <div data-m2v-role="hero-number" style={{
      position: 'absolute', left: x, top: y, transform: translate,
      fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: size, lineHeight: 0.9,
      color, opacity, whiteSpace: 'nowrap', display: 'flex', alignItems: 'baseline',
    }}>
      <MathFormula tex={`${base}^{${exponent}}`} fontSize={size / 1.21} color={color}/>
      {suffix ? <span style={{fontSize: Math.round(size * 0.34), marginLeft: 8}}>{suffix}</span> : null}
    </div>
  );
}

function Page({opacity, children}: {opacity: number; children: ReactNode}) {
  if (opacity <= 0) return null;
  return <div style={{position: 'absolute', inset: 0, opacity}}>{children}</div>;
}

// ---------------------------------------------------------------- S1 第一刀

function FirstCut({frame}: {frame: number}) {
  const opacity = leavePage(180, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.cut, frame);
  const cut = sample.value;
  const depth = cut * 36;
  const notch = `M930 430 L978 ${430 + depth} L1030 430`;
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        {/* 层压木块 */}
        <rect x={700} y={430} width={600} height={290} fill={IVORY} opacity={0.035}
          stroke={IVORY} strokeWidth={1.6} strokeOpacity={0.4}/>
        {Array.from({length: 18}, (_, i) => (
          <line key={i} x1={712} y1={446 + i * 15} x2={1288} y2={446 + i * 15}
            stroke={IVORY} strokeWidth={1} opacity={0.09}/>
        ))}
        <path d={notch} fill="none" stroke={GOLD} strokeWidth={3} strokeLinecap="round"/>
        {/* 凿子 */}
        <g transform={`translate(0 ${-Math.max(0, 8 - cut) * 2})`}>
          <path d="M860 250 L978 300 L978 430 L940 430 L940 330 L860 300 Z"
            fill={IVORY} opacity={0.16} stroke={IVORY} strokeWidth={2.2}
            strokeOpacity={0.7}/>
          <line x1={978} y1={300} x2={978} y2={430} stroke={GOLD} strokeWidth={5}/>
          <circle cx={978} cy={430 + depth} r={4 + breathe(frame, 0, 1.2)} fill={GOLD}/>
        </g>
        {/* 深度尺 */}
        <line x1={640} y1={430} x2={640} y2={720} stroke={LINE} strokeWidth={1.2} opacity={0.5}/>
        {Array.from({length: 9}, (_, i) => (
          <g key={i}>
            <line x1={626} y1={430 + (i / 8) * 290} x2={652} y2={430 + (i / 8) * 290}
              stroke={IVORY} strokeWidth={1.4} opacity={0.45}/>
            <text x={612} y={436 + (i / 8) * 290} textAnchor="end" fontFamily={LATIN}
              fontSize={20} fill={MUTED}>{i}</text>
          </g>
        ))}
        <line x1={620} y1={430 + depth} x2={660} y2={430 + depth} stroke={GOLD}
          strokeWidth={2.4} opacity={0.95}/>
        {/* 木花 */}
        <g transform={`translate(0 ${breathe(frame, 0.5, 1.5)})`}>
          <path d={`M1030 430 C1080 ${420 - depth * 0.4} 1120 ${400 - depth}
            1090 ${380 - depth} C1060 ${368 - depth} 1040 ${405 - depth} 1064 ${418 - depth}`}
            fill="none" stroke={GOLD} strokeWidth={2.4} opacity={0.8}/>
        </g>
        <Burst origin={{x: 978, y: 430 + depth}} progress={frameProgress(frame, 100, 34)}
          count={10} distance={50} rings={1} ringTravel={60} opacity={0.45}/>
      </SvgLayer>
      <RollingFigure value={cut} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={300} y={300} size={180} color={GOLD} decimals={1}/>
      <Label x={620} y={352} size={38} color={GOLD}>mm</Label>
      <Label x={300} y={404} size={40} color={IVORY}>切深</Label>
      <Label x={300} y={452} size={22} color={MUTED}>第 1 刀，切到 8 毫米</Label>
      <Label x={720} y={402} size={26} color={MUTED}>第 1 刀</Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S2 水滴日计数

function SameDrop({frame}: {frame: number}) {
  const opacity = enterPage(180, frame, 0, 8) * leavePage(420, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.drops, frame);
  const count = sample.value;
  const day = Math.max(1, Math.round(count));
  const crack = clamp01(day / 100);
  const dropGold = count < 1.5;
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        {/* 石板 */}
        <path d="M720 540 C780 522 1220 522 1280 540 L1280 760 C1210 780 790 780 720 760 Z"
          fill={IVORY} opacity={0.05} stroke={IVORY} strokeWidth={1.6} strokeOpacity={0.45}/>
        <circle cx={1000} cy={572} r={24} fill="none" stroke={MUTED}
          strokeWidth={1.2} strokeOpacity={0.5}/>
        <circle cx={1000} cy={572} r={10 + ((frame % 18) / 18) * 26} fill="none"
          stroke={GOLD} strokeWidth={1.2} opacity={0.32 * (1 - (frame % 18) / 18)}/>
        {/* 水滴与滴头 */}
        <line x1={1000} y1={214} x2={1000} y2={286} stroke={IVORY}
          strokeWidth={2} opacity={0.35}/>
        <ellipse cx={1000} cy={286} rx={16} ry={8} fill={IVORY} opacity={0.18}/>
        <path d={`M1000 ${302 + ((frame * 7) % 216) - 14}
          C1010 ${302 + ((frame * 7) % 216) - 2}
          ${1009} ${302 + ((frame * 7) % 216) + 9}
          ${1000} ${302 + ((frame * 7) % 216) + 13}
          C${991} ${302 + ((frame * 7) % 216) + 9}
          ${990} ${302 + ((frame * 7) % 216) - 2}
          ${1000} ${302 + ((frame * 7) % 216) - 14} Z`}
          fill={dropGold ? GOLD : IVORY} opacity={dropGold ? 0.95 : 0.62}/>
        {/* 裂纹/凹槽 */}
        <path d={`M1000 572 L1008 ${586 + crack * 30} L994 ${602 + crack * 54}
          L1012 ${620 + crack * 66} L998 ${636 + crack * 72}`}
          fill="none" stroke={GOLD} strokeWidth={2.2 + crack * 1.6} strokeLinecap="round"
          opacity={0.55 + crack * 0.4}/>
        {/* 裂纹随天数变深；不再用底部 100 格标尺 */}
        <text x={1470} y={446} textAnchor="middle" fontFamily={SANS} fontSize={19}
          fill={MUTED} opacity={0.8}>第 1 滴 → 第 100 天 · 99 个间隔</text>
      </SvgLayer>
      <RollingFigure value={count} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={300} y={300} size={180} color={GOLD}/>
      <Label x={300} y={404} size={40} color={IVORY}>滴</Label>
      <Label x={300} y={452} size={22} color={MUTED}>同一滴水，同一块石头</Label>
      <div style={{position: 'absolute', left: 1470, top: 300, transform: 'translate(-50%, -50%)',
        textAlign: 'center', opacity: 0.95}}>
        <div style={{fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: 88, lineHeight: 0.9,
          color: IVORY}}>{day}</div>
        <div style={{fontFamily: SANS, fontSize: 26, color: MUTED, marginTop: 4}}>天</div>
      </div>
      <Label x={1470} y={412} size={21} color={MUTED} align="center">1 滴 / 天</Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S3 数字滚动

function HundredCuts({frame}: {frame: number}) {
  const opacity = enterPage(420, frame, 0, 8) * leavePage(600, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.cuts, frame);
  const count = sample.value;
  const marks = Math.floor(count);
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        {/* 计数器外壳 */}
        <rect x={500} y={278} width={920} height={252} rx={10} fill={T.colors.ink}
          opacity={0.62} stroke={LINE} strokeWidth={1.4} strokeOpacity={0.45}/>
        {[0, 1, 2, 3, 4, 5].map(i => (
          <line key={i} x1={500 + i * 184} y1={278} x2={500 + i * 184} y2={530}
            stroke={LINE} strokeWidth={1} opacity={0.13}/>
        ))}
        {/* 同一块层压木块 + 100 个缺口 */}
        <rect x={470} y={640} width={980} height={116} fill={IVORY} opacity={0.03}
          stroke={IVORY} strokeWidth={1.3} strokeOpacity={0.3}/>
        {Array.from({length: 100}, (_, i) => {
          const passed = i < marks;
          const slip = i === 36;
          const reconnect = i === 37;
          const x = 500 + i * 9.2 + (reconnect ? 4 : 0);
          return <g key={i}>
            <line x1={x} y1={650} x2={x + (slip ? 7 : 0)} y2={passed ? 730 : 740}
              stroke={i === 99 ? GOLD : slip ? EMBER : passed ? IVORY : LINE}
              strokeWidth={i === 99 ? 3.4 : reconnect ? 1.8 : 1.2}
              opacity={passed ? (slip ? 0.95 : 0.62 + Math.sin(frame / 28 + i) * 0.05) : 0.12}/>
            {i === 99 && passed ? <circle cx={x} cy={646} r={4.5} fill={GOLD}/> : null}
            {slip && passed ? <line x1={x - 8} y1={744} x2={x + 15} y2={722}
              stroke={EMBER} strokeWidth={1.8} opacity={0.85}/> : null}
          </g>;
        })}
        <text x={500} y={776} fontFamily={SANS} fontSize={19} fill={MUTED}
          opacity={0.75}>第 37 刀滑，第 38 刀补位；第 100 刀，刃口发金</text>
        {/* 凿子 + 磨刀石 */}
        <g transform={`translate(1400 ${560 + Math.sin(frame / 22) * 2}) scale(1.5)`}>
          <path d="M0 0 L-70 18 L-70 44 L0 28 Z" fill={IVORY} opacity={0.22}
            stroke={IVORY} strokeWidth={1.8} strokeOpacity={0.65}/>
          <line x1={0} y1={0} x2={0} y2={30} stroke={marks >= 100 ? GOLD : IVORY}
            strokeWidth={marks >= 100 ? 5 : 3} opacity={marks >= 100 ? 1 : 0.65}/>
          {marks >= 37 ? <line x1={-2} y1={9} x2={7} y2={16} stroke={EMBER}
            strokeWidth={2.4} opacity={0.9}/> : null}
        </g>
        <ellipse cx={700} cy={600} rx={58} ry={16} fill={IVORY} opacity={0.08}
          stroke={IVORY} strokeWidth={1} strokeOpacity={0.3}/>
        <text x={700} y={630} textAnchor="middle" fontFamily={SANS} fontSize={18}
          fill={MUTED}>磨刀石</text>
        <Burst origin={{x: 500 + 99 * 9.2, y: 700}} progress={frameProgress(frame, 560, 26)}
          count={10} distance={50} rings={1} ringTravel={60} opacity={0.45}/>
      </SvgLayer>
      <RollingFigure value={count} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={960} y={400} size={212} color={GOLD} align="center"/>
      <Label x={1232} y={442} size={42} color={IVORY}>刀</Label>
      <Label x={960} y={548} size={28} color={MUTED} align="center">同一把凿子，每次磨</Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S4 复利定义

function CompoundLoop({frame}: {frame: number}) {
  const opacity = enterPage(600, frame, 0, 8) * leavePage(720, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.loop, frame);
  const loop = sample.value;
  const loopT = ((frame - 612) / 80) % 1;
  const mt = 1 - loopT;
  // 回环是闭合的：下半弧把产出接到投入，上半弧把投入接回产出；光点走完整圈。
  const circuitT = ((frame - 612) / 160) % 1;
  const upper = circuitT >= 0.5;
  const u = upper ? (circuitT - 0.5) * 2 : circuitT * 2;
  const mu = 1 - u;
  const dotX = upper
    ? mu ** 3 * 1160 + 3 * mu ** 2 * u * 1160 + 3 * mu * u ** 2 * 760 + u ** 3 * 760
    : mu ** 3 * 760 + 3 * mu ** 2 * u * 760 + 3 * mu * u ** 2 * 1160 + u ** 3 * 1160;
  const dotY = upper
    ? mu ** 3 * 660 + 3 * mu ** 2 * u * 540 + 3 * mu * u ** 2 * 540 + u ** 3 * 660
    : mu ** 3 * 660 + 3 * mu ** 2 * u * 820 + 3 * mu * u ** 2 * 820 + u ** 3 * 660;
  const markers = [
    {x: 786, y: 760, label: '再投入'},
    {x: 960, y: 812, label: '时间'},
    {x: 1134, y: 760, label: '反馈'},
  ];
  return (
    <Page opacity={opacity}>
      <BilingualTitle zh="复利" en="COMPOUNDING" x={760} y={322} size={200}
        align="center" ruleWidth={80} ruleProgress={loop}/>
      <SvgLayer>
        <path d="M760 660 C760 820 1160 820 1160 660" fill="none" stroke={GOLD}
          strokeWidth={4} strokeLinecap="round" pathLength={1}
          strokeDasharray={`${Math.min(1, loop * 2)} 1`}/>
        <path d="M1160 660 C1160 540 760 540 760 660" fill="none" stroke={GOLD}
          strokeWidth={4} strokeLinecap="round" pathLength={1}
          strokeDasharray={`${Math.max(0, loop * 2 - 1)} 1`}/>
        <path d="M1160 660 L1144 628 M1160 660 L1176 628" stroke={GOLD}
          strokeWidth={3} strokeLinecap="round" opacity={Math.max(0, loop * 2 - 1)}/>
        <path d="M760 660 L744 692 M760 660 L776 692" stroke={GOLD}
          strokeWidth={3} strokeLinecap="round" opacity={Math.max(0, loop * 2 - 1)}/>
        {markers.map((marker, index) => {
          const on = loop > 0.25 + index * 0.24;
          return <g key={marker.label} opacity={on ? 1 : 0.25}>
            <circle cx={marker.x} cy={marker.y} r={5} fill={on ? GOLD : MUTED}/>
            <text x={marker.x} y={marker.y + 28} textAnchor="middle" fontFamily={SANS}
              fontSize={21} fill={on ? IVORY : MUTED}>{marker.label}</text>
          </g>;
        })}
        <circle cx={1160} cy={660} r={4 + beatPulse(frame / 1799, 60, T.motion.bpm, 0.2) * 2}
          fill={GOLD}/>
        <circle cx={dotX} cy={dotY} r={30} fill={GOLD}
          opacity={Math.min(0.28, loop * 0.32)}/>
        <circle cx={dotX} cy={dotY} r={8} fill={GOLD} opacity={Math.min(1, loop * 1.2)}/>
        <circle cx={1400} cy={620} r={62} fill="none" stroke={LINE} strokeWidth={1.2} opacity={0.25}/>
        <circle cx={1400} cy={620} r={62} fill="none" stroke={GOLD} strokeWidth={2.4}
          pathLength={1} strokeDasharray={`${loop} 1`} transform="rotate(-90 1400 620)"/>
      </SvgLayer>
      <RollingFigure value={sample.value} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={1400} y={620} size={82} color={GOLD} align="center" suffix=" 次"/>
      <Label x={1400} y={706} size={22} color={MUTED} align="center">再投入次数</Label>
      <Label x={760} y={632} size={28} color={IVORY} align="center">产出</Label>
      <Label x={1160} y={632} size={28} color={IVORY} align="center">投入</Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S5 二叉分叉

function DoublingTree({frame}: {frame: number}) {
  const opacity = enterPage(720, frame, 0, 8) * leavePage(900, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.turns, frame);
  const turns = sample.value;
  const count = Math.pow(2, turns);
  const current = Math.min(6, Math.floor(turns));
  const levels = 6;
  const rootY = 760;
  const stepY = 82;
  const spread = 880;
  type Node = {x: number; y: number; level: number; index: number};
  const nodes: Node[] = [];
  for (let level = 0; level <= levels; level += 1) {
    const number = Math.pow(2, level);
    for (let index = 0; index < number; index += 1) {
      const offset = number <= 1 ? 0 : (index - (number - 1) / 2) * (spread / (number - 1));
      nodes.push({x: CX + offset, y: rootY - level * stepY, level, index});
    }
  }
  const edges: Array<{from: Node; to: Node}> = [];
  for (let level = 1; level <= levels; level += 1) {
    for (let index = 0; index < Math.pow(2, level); index += 1) {
      const to = nodes.find(node => node.level === level && node.index === index);
      const from = nodes.find(node => node.level === level - 1 && node.index === Math.floor(index / 2));
      if (to && from) edges.push({from, to});
    }
  }
  const leafOpacity = Math.pow(2, turns) / 64;
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        {edges.map((edge, index) => {
          const on = edge.to.level <= current;
          return <line key={index} x1={edge.from.x} y1={edge.from.y} x2={edge.to.x} y2={edge.to.y}
            stroke={GOLD} strokeWidth={on ? 1.2 : 0.6}
            opacity={on ? 0.28 + edge.to.level * 0.07 : 0.06}/>;
        })}
        {nodes.map(node => {
          const on = node.level < current || (node.level === current && turns > 0.05);
          const leaf = node.level === levels;
          return <circle key={`${node.level}-${node.index}`} cx={node.x} cy={node.y}
            r={leaf ? 2.6 : node.level === current ? 4.2 : 2.2}
            fill={leaf ? GOLD : node.level === current ? IVORY : GOLD}
            opacity={on ? (leaf ? 0.35 + leafOpacity * 0.55 : 0.55 + node.level * 0.05) : 0.08}/>;
        })}
        <circle cx={CX} cy={rootY} r={5 + breathe(frame, 0, 1)} fill={GOLD}/>
        <text x={CX} y={806} textAnchor="middle" fontFamily={SANS} fontSize={20}
          fill={MUTED}>1 个起点</text>
      </SvgLayer>
      <RollingFigure value={count} previous={Math.pow(2, sample.previous)}
        previous2={Math.pow(2, sample.previous2)}
        speed={Math.abs(count - Math.pow(2, sample.previous)) / 2}
        x={140} y={300} size={200} color={GOLD} suffix="×"/>
      <Label x={140} y={402} size={38} color={IVORY}>第 {Math.max(1, Math.ceil(turns))} 层</Label>
      <Label x={140} y={448} size={22} color={MUTED}>每分一次，枝数翻倍</Label>
      <Label x={140} y={500} size={21} latin color={MUTED}>EACH SPLIT DOUBLES</Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S6 42 折 + 曲线

function FoldToCurve({frame}: {frame: number}) {
  const opacity = enterPage(900, frame, 0, 8) * leavePage(1080, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.folds, frame);
  const fold = sample.value;
  const chartX = 680;
  const chartW = 840;
  const chartTop = 300;
  const chartH = 520;
  const chartBase = chartTop + chartH;
  const moonY = 365;
  const {y: topY} = paperStackTop(fold, moonY);
  const top = Math.max(120, topY);
  const base = 820;
  const curveT = clamp01((frame - 1000) / 40);
  const stackFade = 1 - clamp01((frame - 1000) / 24);
  const xAt = (n: number) => chartX + (n / 42) * chartW;
  const yAt = (n: number) => chartBase - chartH * curveValue('paper', n / 42);
  const curvePointsList = Array.from({length: SAMPLE}, (_, index) => {
    const n = (index / (SAMPLE - 1)) * 42;
    return [xAt(n), yAt(n)] as [number, number];
  });
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        <g opacity={stackFade}>
          <line x1={1050} y1={moonY} x2={1370} y2={moonY} stroke={MUTED}
            strokeWidth={1.4} strokeDasharray="6 8" opacity={0.45}/>
          <circle cx={1400} cy={moonY} r={26} fill={IVORY} opacity={0.75}/>
          <text x={1400} y={moonY - 44} textAnchor="middle" fontFamily={SANS} fontSize={24}
            fill={MUTED}>地月 38.44 万 km</text>
        </g>
        <g opacity={stackFade} transform={`rotate(${curveT * 90} 975 540)`}>
          <rect x={900} y={top} width={150} height={Math.max(0, base - top)}
            fill={GOLD} opacity={0.13} stroke={GOLD} strokeWidth={1.4} strokeOpacity={0.55}/>
          {Array.from({length: 21}, (_, i) => (
            <line key={i} x1={900} y1={top + (i / 20) * Math.max(0, base - top)}
              x2={1050} y2={top + (i / 20) * Math.max(0, base - top)}
              stroke={i % 2 === 0 ? GOLD : IVORY} strokeWidth={1}
              opacity={0.35 + i * 0.025}/>
          ))}
          <circle cx={975} cy={top} r={4 + breathe(frame, 0, 1.4)} fill={GOLD}/>
        </g>
        {curveT > 0 ? <g opacity={curveT}>
          <ChartFrame x={chartX} y={chartTop} width={chartW} height={chartH}
            xTicks={[0, 10 / 42, 20 / 42, 30 / 42, 1]} xLabels={['0', '10', '20', '30', '42']}
            yTicks={[0, 1]} yLabels={['0.1 mm', '439,804 km']} opacity={0.7}/>
          <line x1={1280} y1={moonY} x2={chartX + chartW + 26} y2={moonY} stroke={MUTED}
            strokeWidth={1.4} strokeDasharray="6 8" opacity={0.5}/>
          <circle cx={chartX + chartW + 46} cy={moonY} r={18} fill={IVORY} opacity={0.7}/>
          <text x={chartX + chartW + 74} y={moonY + 7} fontFamily={SANS} fontSize={22}
            fill={MUTED}>地月 38.44 万 km</text>
          <ChartLine points={curvePointsList} color={GOLD} width={4} progress={curveT}/>
          {[10, 20, 30, 42].map((n, index) => (
            <ChartMarker key={n} x={xAt(n)} y={yAt(n)} radius={8}
              color={curveT > index / 4 ? GOLD : MUTED} halo={curveT > index / 4}
              opacity={curveT > index / 4 ? 1 : 0.35}
              label={`2^${n}`} labelColor={GOLD} labelY={yAt(n) - 22} labelSize={22}/>
          ))}
          <circle cx={lerp(chartX, chartX + chartW, curveT)} cy={yAt(curveT * 42)} r={5} fill={GOLD}/>
          <text x={chartX + chartW + 24} y={chartBase + 34} fontFamily={LATIN} fontSize={22}
            fill={MUTED}>FOLDS</text>
        </g> : null}
        <Burst origin={{x: 975, y: top}} progress={frameProgress(frame, 1000, 32)}
          count={14} distance={80} rings={2} ringTravel={110} opacity={0.55}/>
      </SvgLayer>
      <RollingFigure value={fold} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={140} y={290} size={110} color={GOLD} suffix=" 折"/>
      <Power base="2" exponent={String(Math.round(fold))} x={140} y={410} size={110} color={GOLD}/>
    </Page>
  );
}

// ---------------------------------------------------------------- S7 两种堆法

function TwoPiles({frame}: {frame: number}) {
  if (frame >= 1230) return null;
  const opacity = enterPage(1080, frame, 0, 8);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.steps, frame);
  const step = sample.value;
  const {y: compoundTop} = paperStackTop(step);
  const top = Math.max(120, compoundTop);
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        {/* 左：线性堆 + 放大镜 */}
        <circle cx={690} cy={600} r={92} fill={T.colors.ink} opacity={0.55}
          stroke={LINE} strokeWidth={1.2}/>
        {Array.from({length: 42}, (_, i) => (
          <line key={i} x1={628} y1={680 - i * 1.4} x2={752} y2={680 - i * 1.4}
            stroke={i < step ? IVORY : LINE} strokeWidth={1}
            opacity={i < step ? 0.55 : 0.12}/>
        ))}
        <circle cx={690} cy={600} r={92} fill="none" stroke={GOLD}
          strokeWidth={2} opacity={0.5}/>
        {/* 右：翻倍堆 */}
        <rect x={1120} y={top} width={150} height={Math.max(0, 820 - top)}
          fill={GOLD} opacity={0.14} stroke={GOLD} strokeWidth={1.4} strokeOpacity={0.55}/>
        <circle cx={1195} cy={top} r={5} fill={GOLD}/>
        <line x1={1050} y1={220} x2={1370} y2={220} stroke={MUTED}
          strokeWidth={1.4} strokeDasharray="6 8" opacity={0.45}/>
        <text x={1400} y={176} textAnchor="middle" fontFamily={SANS} fontSize={24}
          fill={MUTED}>地月 38.44 万 km</text>
      </SvgLayer>
      <Label x={690} y={724} size={28} color={IVORY} align="center">线性 4.2 mm</Label>
      <Label x={690} y={760} size={20} color={MUTED} align="center">42 张 × 0.1 mm</Label>
      <Label x={1195} y={850} size={28} color={GOLD} align="center">复利 43.98 万 km</Label>
      <Label x={1195} y={886} size={20} color={MUTED} align="center">42 次翻倍</Label>
      <RollingFigure value={step} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={300} y={300} size={124} color={GOLD} suffix=" 步"/>
    </Page>
  );
}

// ---------------------------------------------------------------- S8 网络

function NetworkRatio({frame}: {frame: number}) {
  if (frame < 1230) return null;
  const opacity = leavePage(1410, frame, 4);
  if (opacity <= 0) return null;
  const left = sampleTimeline(TL.left, frame);
  const right = sampleTimeline(TL.right, frame);
  const ratio = left.value > 0.5 ? right.value / left.value : 0;
  const ratioPrev = left.previous > 0.5 ? right.previous / left.previous : ratio;
  const ratioPrev2 = left.previous2 > 0.5 ? right.previous2 / left.previous2 : ratioPrev;
  const ratioSpeed = Math.abs(ratio - ratioPrev) / 2;
  const ratioReveal = clamp01(right.value / 120);
  const ratioOpacity = clamp01((ratio - 20.8) / 0.2);
  const nodes = networkNodes(100, 300);
  const arc = (radius: number, from: number, to: number) => {
    const x0 = CX + Math.cos(from) * radius;
    const y0 = CY + Math.sin(from) * radius;
    const x1 = CX + Math.cos(to) * radius;
    const y1 = CY + Math.sin(to) * radius;
    const large = to - from > Math.PI ? 1 : 0;
    return `M${x0} ${y0} A${radius} ${radius} 0 ${large} 1 ${x1} ${y1}`;
  };
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        <g transform={`rotate(${(frame - 1230) * 0.025} 960 520)`}>
        <circle cx={CX} cy={CY} r={300} fill="none" stroke={LINE} strokeWidth={1} opacity={0.14}/>
        {nodes.map((node, index) => {
          const first = index < 10;
          const last = index >= 90;
          return <circle key={index} cx={node.x} cy={node.y}
            r={first || last ? 5.5 : 2.4}
            fill={first || last ? GOLD : IVORY}
            opacity={first || last ? 0.92 : 0.18}/>;
        })}
        <path d={firstTenPath(300)} fill="none" stroke={GOLD} strokeWidth={1.4}
          opacity={0.8} pathLength={1} strokeDasharray={`${clamp01(left.value / 45)} 1`}/>
        <path d={lastTenPath(300)} fill="none" stroke={GOLD} strokeWidth={0.9}
          opacity={0.38} pathLength={1} strokeDasharray={`${clamp01(right.value / 945)} 1`}/>
        <path d={arc(322, -0.1, 0.62)} fill="none" stroke={IVORY} strokeWidth={1.4} opacity={0.35}/>
        <path d={arc(322, 5.52, 6.38)} fill="none" stroke={GOLD} strokeWidth={1.4} opacity={0.45}/>
        </g>
        <ShockRing origin={{x: CX, y: CY}} progress={frameProgress(frame, 1230, 24)}
          count={1} travel={300} thickness={2} dashes="0.03 0.02" opacity={0.65}/>
      </SvgLayer>
      <Label x={1288} y={300} size={30} color={IVORY} align="left">前 10 个内部</Label>
      <RollingFigure value={left.value} previous={left.previous} previous2={left.previous2}
        speed={left.speed} x={1288} y={352} size={32} color={MUTED} align="left" suffix=" 条"/>
      <Label x={1288} y={700} size={30} color={GOLD} align="left">最后 10 个新增</Label>
      <RollingFigure value={right.value} previous={right.previous} previous2={right.previous2}
        speed={right.speed} x={1288} y={752} size={32} color={GOLD} align="left" suffix=" 条"/>
      <div style={{position: 'absolute', inset: 0, opacity: ratioReveal,
        transform: `scale(${1 + beatPulse(frame / 1799, 60, T.motion.bpm, 0.2) * 0.015})`,
        transformOrigin: '960px 520px'}}>
        <RollingFigure value={ratio} previous={ratioPrev} previous2={ratioPrev2}
          speed={ratioSpeed} x={960} y={520} size={180} color={IVORY}
          align="center" suffix="×"/>
      </div>
      <Label x={960} y={630} size={27} color={IVORY} align="center" opacity={ratioOpacity}>
        最后 10 个新增，连接数 21 倍
      </Label>
      <Label x={960} y={178} size={24} color={MUTED} align="center">
        100 个概念 / 4,950 条连接
      </Label>
    </Page>
  );
}

// ---------------------------------------------------------------- S9 棋盘

function Chessboard({frame}: {frame: number}) {
  const opacity = enterPage(1410, frame, 0, 8) * leavePage(1560, frame, 4);
  if (opacity <= 0) return null;
  const sample = sampleTimeline(TL.cells, frame);
  const cells = sample.value;
  const size = 560;
  const cell = size / 8;
  const left = CX - size / 2;
  const top = CY - size / 2;
  const current = Math.max(0, Math.min(63, Math.floor(cells) - 1));
  const scale = 1 - clamp01((frame - 1410) / 150) * 0.1;
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        <g transform={`translate(960 540) scale(${scale}) translate(-960 -540)`}>
          <rect x={left} y={top} width={size} height={size} fill={T.colors.ink} opacity={0.9}/>
          {Array.from({length: 64}, (_, i) => {
            const row = Math.floor(i / 8);
            const col = i % 8;
            const visible = i < cells;
            // 每 10 格翻一倍，与「每格翻倍」同构；格内最多画 40 粒。
            const grains = Math.min(40, Math.round(Math.pow(2, i / 10)));
            return <g key={i} opacity={visible ? 1 : 0.1}>
              <rect x={left + col * cell + 1} y={top + row * cell + 1}
                width={cell - 2} height={cell - 2} fill={GOLD}
                opacity={i === current ? 0.45 : visible ? 0.07 + (i / 63) * 0.23 : 0}/>
              {visible ? Array.from({length: grains}, (_, dot) => (
                <ellipse key={dot} cx={left + col * cell + 6 + (dot % 8) * 8}
                  cy={top + row * cell + 9 + Math.floor(dot / 8) * 12.6}
                  rx={2.4} ry={3} fill={GOLD} opacity={0.55 + (i / 63) * 0.25}/>
              )) : null}
            </g>;
          })}
          {Array.from({length: 7}, (_, i) => (
            <g key={i} opacity={0.35}>
              <line x1={left + (i + 1) * cell} y1={top} x2={left + (i + 1) * cell}
                y2={top + size} stroke={LINE} strokeWidth={1.1}/>
              <line x1={left} y1={top + (i + 1) * cell} x2={left + size}
                y2={top + (i + 1) * cell} stroke={LINE} strokeWidth={1.1}/>
            </g>
          ))}
          <Burst origin={{x: left + 7 * cell + cell / 2, y: top + 7 * cell + cell / 2}}
            progress={frameProgress(frame, 1545, 30)} count={18} distance={80}
            rings={2} ringTravel={110} opacity={0.55}/>
          <text x={left + cell / 2} y={top - 12} textAnchor="middle" fontFamily={LATIN}
            fontSize={20} fill={GOLD}>1</text>
          <text x={left + 7 * cell + cell / 2} y={top + size + 24} textAnchor="middle"
            fontFamily={LATIN} fontSize={20} fill={GOLD}>64</text>
          <text x={left + size + 18} y={top + 22} fontFamily={LATIN} fontSize={21}
            fill={MUTED}>8 × 8</text>
        </g>
      </SvgLayer>
      <Power base="2" exponent="63" x={220} y={580} size={150} color={GOLD}/>
      <Label x={220} y={666} size={32} color={IVORY}>最后一格</Label>
      <Label x={220} y={708} size={21} color={MUTED}>全盘 2⁶⁴−1 粒</Label>
      <RollingFigure value={cells} previous={sample.previous} previous2={sample.previous2}
        speed={sample.speed} x={220} y={790} size={68} color={GOLD} suffix=" 格已填"/>
    </Page>
  );
}

// ---------------------------------------------------------------- S10 99 + 接

function NinetyNineAndGlyph({frame}: {frame: number}) {
  const opacity = enterPage(1560, frame, 0, 8);
  if (opacity <= 0) return null;
  const loopSample = sampleTimeline(TL.loop99, frame);
  const finalSample = sampleTimeline(TL.final, frame);
  const phase = clamp01((frame - 1646) / 18);
  const textOut = 1 - clamp01((frame - 1646) / 12);
  const countIn = clamp01((frame - 1652) / 8);
  const netPhase = clamp01((frame - 1740) / 28);
  const glyphProgress = clamp01(finalSample.value / 4950);
  const glyphOpacity = textFade(frame, 1658, 1762, 10);
  const title = textFade(frame, 1762, 1810, 8);
  const pulse = beatPulse(frame / 1799, 60, T.motion.bpm, 0.2);
  const threads = loopThreads(100, 360);
  return (
    <Page opacity={opacity}>
      <SvgLayer>
        <defs>
          <clipPath id="cc4-glyph" clipPathUnits="userSpaceOnUse">
            <text x={960} y={760} textAnchor="middle" fontFamily={SANS}
              fontSize={620} fontWeight={400}>接</text>
          </clipPath>
          <radialGradient id="cc4-dot">
            <stop offset="0" stopColor={T.light.core} stopOpacity="0.9"/>
            <stop offset="0.4" stopColor={GOLD} stopOpacity="0.35"/>
            <stop offset="1" stopColor={GOLD} stopOpacity="0"/>
          </radialGradient>
        </defs>
        <g opacity={1 - phase}>
          <circle cx={CX} cy={CY} r={360} fill="none" stroke={IVORY} strokeWidth={1.2}
            opacity={0.12}/>
          {threads.map(([from, to], index) => {
            const visible = Math.max(0, Math.min(1, (loopSample.value - index) / 3));
            return <line key={index} x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke={index === threads.length - 1 ? GOLD : IVORY}
              strokeWidth={index === threads.length - 1 ? 1.6 : 1}
              opacity={visible * (index === threads.length - 1 ? 0.7 : 0.26)}/>;
          })}
          <circle cx={CX} cy={CY} r={90 + pulse * 14} fill="url(#cc4-dot)"
            opacity={0.55 + pulse * 0.1}/>
          <circle cx={CX} cy={CY} r={9 + pulse * 1.8} fill={GOLD}/>
        </g>
        <g opacity={textOut}>
          <text x={CX} y={640} textAnchor="middle" dominantBaseline="central"
            fontFamily={LATIN} fontSize={76} fill={GOLD}>{Math.round(loopSample.value)}</text>
          <text x={CX} y={700} textAnchor="middle" fontFamily={SANS} fontSize={28}
            fill={IVORY}>第一个点的最终连接数</text>
          <text x={CX} y={738} textAnchor="middle" fontFamily={LATIN} fontSize={20}
            fill={MUTED} letterSpacing="0.16em">THE FIRST NODE</text>
        </g>
        <g clipPath="url(#cc4-glyph)" opacity={glyphOpacity}>
          <g transform={`rotate(${(frame - 1665) * 0.055} 960 520)`}>
            <path d={allChordsPath(100, 360)} fill="none" stroke={GOLD}
              strokeWidth={1.2} opacity={0.55} pathLength={1}
              strokeDasharray={`${glyphProgress} 1`}/>
          </g>
        </g>
        <g opacity={netPhase * 0.5}
          transform="translate(1520 460) scale(0.64) translate(-960 -520)">
          <circle cx={CX} cy={CY} r={360} fill="none" stroke={IVORY} strokeWidth={1.6}
            opacity={0.12}/>
          {networkNodes(100, 360).map((node, index) => {
            const first = index < 10;
            const last = index >= 90;
            return <circle key={index} cx={node.x} cy={node.y}
              r={first || last ? 7 : 4}
              fill={first ? GOLD : IVORY}
              opacity={first ? 0.95 : last ? 0.55 : 0.32}/>;
          })}
          {loopThreads(100, 360).map(([from, to], index) => (
            <line key={`t${index}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke={GOLD} strokeWidth={1} opacity={0.22}/>
          ))}
          <path d={allChordsPath(100, 360)} fill="none" stroke={GOLD}
            strokeWidth={0.7} opacity={0.08} pathLength={1}
            strokeDasharray={`${glyphProgress} 1`}/>
        </g>
        <circle cx={960} cy={520} r={130 + pulse * 10} fill="url(#cc4-dot)" opacity={glyphOpacity * 0.65}/>
        <circle cx={960} cy={520} r={9 + pulse * 2} fill={GOLD} opacity={glyphOpacity}/>
        <ShockRing origin={{x: 960, y: 520}} progress={frameProgress(frame, 1560, 34)}
          count={1} travel={280} thickness={2.2} opacity={0.5}/>
      </SvgLayer>
      <RollingFigure value={finalSample.value} previous={finalSample.previous}
        previous2={finalSample.previous2} speed={finalSample.speed} x={140} y={230}
        size={70} color={GOLD} opacity={countIn * 0.95} suffix=" 条连接"/>
      <div style={{position: 'absolute', inset: 0,
        transform: `scale(${1 + Math.sin(frame / 60) * 0.002})`,
        transformOrigin: '290px 438px'}}>
        <BilingualTitle zh="接" en="COMPOUNDING" x={140} y={438} size={300}
          opacity={title} ruleWidth={96} ruleProgress={title}/>
        <Label x={140} y={690} size={32} color={GOLD} opacity={title}>复利不是钱的事</Label>
      </div>
      <Label x={1520} y={736} size={22} color={MUTED} align="center" opacity={netPhase * 0.8}>
        100 个概念 · 全部互连
      </Label>
    </Page>
  );
}

const SUBTITLE_VARIANTS: Record<number, SubtitleVariant> = {
  10: {enter: 'rise', exit: 'drift', englishDelayFrames: 10},
  196: {enter: 'wipe', exit: 'mask', englishDelayFrames: 8},
  436: {enter: 'settle', exit: 'drift', englishDelayFrames: 8},
  616: {enter: 'rise', exit: 'dissolve', englishDelayFrames: 8},
  736: {enter: 'settle', exit: 'mask', englishDelayFrames: 8},
  916: {enter: 'wipe', exit: 'drift', englishDelayFrames: 8},
  1096: {enter: 'rise', exit: 'mask', englishDelayFrames: 8},
  1292: {enter: 'wipe', exit: 'drift', englishDelayFrames: 6},
  1350: {enter: 'rise', exit: 'mask', englishDelayFrames: 6},
  1426: {enter: 'settle', exit: 'mask', englishDelayFrames: 8},
  1576: {enter: 'rise', exit: 'dissolve', englishDelayFrames: 10},
};
const SUBTITLE_EMPHASIS = /100|99|37|64|42|4\.2|439,804\.65|45|945|21|4,950|63|复利|接/;

type Subtitle = {startFrame: number; endFrame: number; text: string};
type Props = {screenSubtitles?: Subtitle[]};

function MethodNote({frame}: {frame: number}) {
  return (
    <div style={{
      position: 'absolute', right: 48, top: 1000, textAlign: 'right',
      fontFamily: SANS, fontSize: 21, lineHeight: 1.35, color: MUTED,
      opacity: textFade(frame, 120, 1790, 20) * 0.82,
    }}>
      故事为示意；水滴/日计数为示意（1 滴/天）；纸厚 0.1 mm、可无限对折；棋盘每格翻倍；网络每两个概念一条连接。
      <div style={{fontFamily: LATIN, fontSize: 18, letterSpacing: '0.08em',
        marginTop: 2, textTransform: 'uppercase'}}>
        a schematic story · one drop a day · 0.1 mm paper · doubling board · one link per pair
      </div>
    </div>
  );
}

export default function CompoundConnect({props, width, height, subtitleSafeArea, fps}: CodeSceneProps) {
  const {elapsedSeconds, ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    void ensureMathReady().then(ready);
  }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  const subtitles = ((props as unknown as Props).screenSubtitles ?? []) as Subtitle[];
  const pulse = beatPulse(frame / 1799, 60, T.motion.bpm, 0.2);
  return (
    <Stage width={width} height={height}>
      <FirstCut frame={frame}/>
      <SameDrop frame={frame}/>
      <HundredCuts frame={frame}/>
      <CompoundLoop frame={frame}/>
      <DoublingTree frame={frame}/>
      <FoldToCurve frame={frame}/>
      <TwoPiles frame={frame}/>
      <NetworkRatio frame={frame}/>
      <Chessboard frame={frame}/>
      <NinetyNineAndGlyph frame={frame}/>
      <HandoffLayer frame={frame}/>
      <MethodNote frame={frame}/>
      <ScreenSubtitle items={subtitles} frame={frame} safeArea={subtitleSafeArea}
        variants={SUBTITLE_VARIANTS} emphasis={SUBTITLE_EMPHASIS} pulse={pulse}
        shimmer={frame / 1799}/>
    </Stage>
  );
}
