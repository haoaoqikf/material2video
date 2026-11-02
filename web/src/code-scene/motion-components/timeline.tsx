/** 事件时间轴与章节轨：位置由数值映射，显隐只由 progress 决定。 */
import type {CSSProperties} from 'react';
import {scaleLinear} from 'd3-scale';
import {motionCurve} from '../motion';
import {clampProgress, type Easing} from '../primitives';
import {dataAttrs} from './internal';

const LINEAR = motionCurve('linear');

export type TimelineItem = {
  at: number;
  label: string;
  emphasized?: boolean;
};

export type TimelineOrientation = 'horizontal' | 'vertical';

export type TimelineProps = {
  items: readonly TimelineItem[];
  progress: number;
  easing?: Easing;
  orientation?: TimelineOrientation;
  domain?: readonly [number, number];
  width?: number;
  height?: number;
  color?: string;
  accentColor?: string;
  labelColor?: string;
  fontSize?: number;
  fontFamily?: string;
  thickness?: number;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 事件轴；标签不做自动避让，密集时由调用方错开或合并。 */
export function Timeline({
  items, progress, easing = LINEAR, orientation = 'horizontal', domain, width = 1200,
  height = 160, color = 'rgba(255, 255, 255, 0.45)', accentColor = '#F8D893',
  labelColor = '#F3EDDC', fontSize = 18, fontFamily = 'M2V Sans, sans-serif',
  thickness = 2, className, style, role, state,
}: TimelineProps) {
  const ended = Math.max(0, ...items.map(item => item.at));
  const [from, to] = domain ?? [0, ended || 1];
  const horizontal = orientation === 'horizontal';
  const axisAt = horizontal ? height * 0.6 : width * 0.35;
  const start = horizontal ? 24 : 24;
  const end = horizontal ? width - 24 : height - 24;
  const scale = scaleLinear().domain([from, to]).range([start, end]);
  const eased = easing(clampProgress(progress));
  const lineEnd = start + (end - start) * eased;
  const axisLine = horizontal
    ? {x1: start, x2: lineEnd, y1: axisAt, y2: axisAt}
    : {x1: axisAt, x2: axisAt, y1: start, y2: lineEnd};
  return (
    <svg {...dataAttrs(role, state)} className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`} style={{overflow: 'visible', ...style}}>
      <line {...axisLine} stroke={color} strokeWidth={thickness} strokeLinecap="round"/>
      {items.map((item, index) => {
        const position = scale(item.at);
        const visible = (position - start) / (end - start) <= eased + 1e-9;
        if (!visible) return null;
        const accent = item.emphasized ? accentColor : labelColor;
        const radius = item.emphasized ? 7 : 5;
        return horizontal ? (
          <g key={index}>
            <line x1={position} x2={position} y1={axisAt - 12} y2={axisAt + 12} stroke={accent}
              strokeWidth={thickness}/>
            <circle cx={position} cy={axisAt} r={radius} fill={accent}/>
            <text x={position} y={axisAt - 22} fill={accent} fontFamily={fontFamily}
              fontSize={item.emphasized ? fontSize * 1.08 : fontSize} textAnchor="middle">
              {item.label}
            </text>
          </g>
        ) : (
          <g key={index}>
            <line x1={axisAt - 12} x2={axisAt + 12} y1={position} y2={position} stroke={accent}
              strokeWidth={thickness}/>
            <circle cx={axisAt} cy={position} r={radius} fill={accent}/>
            <text x={axisAt + 22} y={position + fontSize * 0.35} fill={accent}
              fontFamily={fontFamily} fontSize={item.emphasized ? fontSize * 1.08 : fontSize}>
              {item.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export type ChapterTrackProps = Omit<TimelineProps, 'items' | 'domain'> & {
  chapters: readonly string[];
};

/** 等距章节轨；当前章节按进度高亮，章节名过长时由调用方自行截断。 */
export function ChapterTrack({
  chapters, progress, ...rest
}: ChapterTrackProps) {
  const count = Math.max(1, chapters.length);
  const active = Math.min(count - 1, Math.floor(clampProgress(progress) * count));
  const items = chapters.map((label, index) => ({at: index, label, emphasized: index === active}));
  return <Timeline {...rest} progress={progress} items={items} domain={[0, Math.max(1, count - 1)]}/>;
}
