/** ELK 只在 layoutDiagram 调用时加载；绘制阶段只消费固定布局。 */
import {useId, type CSSProperties} from 'react';
import type {ElkNode} from 'elkjs/lib/elk-api';
import {chartLinePath} from './chart-geometry';
import {dataAttrs} from './motion-components/internal';

export type DiagramNode = {id: string; label: string; width?: number; height?: number};
export type DiagramEdge = {id: string; source: string; target: string};
export type DiagramLayout = {
  width: number; height: number;
  nodes: Array<DiagramNode & {x: number; y: number; width: number; height: number}>;
  edges: Array<DiagramEdge & {points: Array<[number, number]>}>;
};
export type DiagramOptions = {direction?: 'RIGHT' | 'LEFT' | 'DOWN' | 'UP'; spacing?: number; seed?: number};
const byId = (a: {id: string}, b: {id: string}) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0;

export async function layoutDiagram(nodes: readonly DiagramNode[], edges: readonly DiagramEdge[],
  {direction = 'RIGHT', spacing = 48, seed = 1}: DiagramOptions = {}): Promise<DiagramLayout> {
  if (!nodes.length || nodes.length > 500 || edges.length > 2000) throw new Error('图示须有 1–500 个节点、至多 2000 条边');
  if (!['RIGHT', 'LEFT', 'DOWN', 'UP'].includes(direction) || !Number.isFinite(spacing) || spacing <= 0
    || !Number.isSafeInteger(seed)) throw new Error('图示方向、间距或种子无效');
  const ids = new Set<string>();
  const children = [...nodes].sort(byId).map(node => {
    const width = node.width ?? 220, height = node.height ?? 96;
    if (!node.id || ids.has(node.id) || typeof node.label !== 'string' || ![width, height].every(n => Number.isFinite(n) && n > 0)) {
      throw new Error('图示节点 ID 重复或尺寸/标签无效');
    }
    ids.add(node.id);
    return {id: node.id, label: node.label, width, height};
  });
  const edgeIds = new Set<string>();
  const connections = [...edges].sort(byId).map(edge => {
    if (!edge.id || edgeIds.has(edge.id) || ids.has(edge.id) || !ids.has(edge.source) || !ids.has(edge.target)) throw new Error('图示边 ID 重复或引用未知节点');
    edgeIds.add(edge.id);
    return {id: edge.id, sources: [edge.source], targets: [edge.target]};
  });
  const {default: ELK} = await import('elkjs/lib/elk.bundled.js');
  const elk = new ELK();
  const result = await elk.layout<ElkNode>({id: 'root', layoutOptions: {
    'elk.algorithm': 'layered', 'elk.direction': direction, 'elk.randomSeed': String(seed),
    'elk.spacing.nodeNode': String(spacing), 'elk.layered.spacing.nodeNodeBetweenLayers': String(spacing),
    'elk.edgeRouting': 'ORTHOGONAL',
  }, children, edges: connections});
  return {width: result.width!, height: result.height!,
    // ELK 会向工作对象注入内部状态（如 $H）；仅投影公开字段，不能将其带入缓存。
    nodes: result.children!.map(node => ({id: node.id, label: children.find(item => item.id === node.id)!.label,
      width: node.width!, height: node.height!, x: node.x!, y: node.y!})),
    edges: result.edges!.map(edge => {
      const section = edge.sections?.[0];
      if (!section) throw new Error(`图示边无路由：${edge.id}`);
      return {...edges.find(item => item.id === edge.id)!,
        points: [section.startPoint, ...(section.bendPoints ?? []), section.endPoint].map(p => [p.x, p.y])};
    })};
}

/** 节点尺寸由作者先确定；长标签可通过 renderNode 自定义，默认不截断。 */
export function Diagram({layout, progress = 1, color = '#F3EDDC', background = '#18202B',
  fontSize = 28, style, role, state, renderNode}: {
  layout: DiagramLayout; progress?: number; color?: string; background?: string; fontSize?: number;
  style?: CSSProperties; role?: string; state?: string;
  renderNode?: (node: DiagramLayout['nodes'][number]) => React.ReactNode;
}) {
  const p = Math.max(0, Math.min(1, progress));
  const arrow = `diagram-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return <svg {...dataAttrs(role, state)} viewBox={`0 0 ${layout.width} ${layout.height}`}
    width={layout.width} height={layout.height} style={{overflow: 'visible', ...style}}>
    <defs><marker id={arrow} viewBox="0 0 10 10" refX={9} refY={5} markerWidth={7} markerHeight={7} orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 Z" fill={color}/></marker></defs>
    {layout.edges.map(edge => <path key={edge.id} d={chartLinePath(edge.points)} fill="none" stroke={color}
      strokeWidth={3} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p} markerEnd={p === 1 ? `url(#${arrow})` : undefined}/>)}
    {layout.nodes.map(node => <g key={node.id} transform={`translate(${node.x} ${node.y})`} opacity={p}>
      {renderNode ? renderNode(node) : <><rect width={node.width} height={node.height} rx={12} fill={background} stroke={color}/>
        <text x={node.width / 2} y={node.height / 2} textAnchor="middle" dominantBaseline="central"
          fontSize={fontSize} fill={color}>{node.label}</text></>}
    </g>)}
  </svg>;
}
