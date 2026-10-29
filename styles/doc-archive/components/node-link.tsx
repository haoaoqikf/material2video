/** 节点图：节点与连线；表示网络、地图或关系，不表示实测拓扑。 */
import type {CSSProperties} from 'react';
import {T, alpha, clamp01} from './kit';

export type NodePoint = {x: number; y: number; label?: string};
export type NodeLinkProps = {
  nodes: NodePoint[];
  links: Array<[number, number]>;
  width?: number;
  height?: number;
  accent?: string;
  progress?: number;
  style?: CSSProperties;
  role?: string;
};

export default function NodeLink({
  nodes, links, width = 1050, height = 720, accent = T.colors.copper,
  progress = 0, style, role = 'node-link',
}: NodeLinkProps) {
  const travel = clamp01(progress);
  return (
    <svg
      data-m2v-role={role}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{position: 'absolute', overflow: 'visible', ...style}}
    >
      {links.map(([from, to], index) => {
        const source = nodes[from];
        const target = nodes[to];
        if (!source || !target) return null;
        const reveal = clamp01(travel * links.length - index);
        return (
          <line
            key={`${from}-${to}-${index}`}
            x1={source.x} y1={source.y} x2={target.x} y2={target.y}
            stroke={alpha(accent, 0.5)} strokeWidth={2} opacity={reveal}
          />
        );
      })}
      {nodes.map((node, index) => {
        const reveal = clamp01(travel * nodes.length - index);
        return (
          <g key={index} opacity={0.25 + 0.75 * reveal}>
            <circle cx={node.x} cy={node.y} r={11} fill={T.colors.text} opacity={reveal}/>
            <circle cx={node.x} cy={node.y} r={18} fill="none" stroke={accent} strokeWidth={1.5} opacity={0.5 * reveal}/>
            {node.label && (
              <text x={node.x} y={node.y + 34} fill={T.colors.muted} fontSize={20} textAnchor="middle"
                style={{fontFamily: T.type.fontStack}}>{node.label}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
