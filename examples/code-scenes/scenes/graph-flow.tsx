import { layoutGraph, probe, type A2VCodeScene } from '@a2v/scene';

/**
 * Dagre 稳定布局示例：坐标由输入集合决定，与枚举顺序无关。
 * 节点画成 SVG 圆角矩形，边是折线路径；全部为本地绘制，无外部引用。
 */
interface GraphNodeInput {
  id: string;
  label: string;
  width: number;
  height: number;
}

interface GraphEdgeInput {
  from: string;
  to: string;
}

const GraphFlow: A2VCodeScene<{
  kicker: string;
  caption: string;
  nodes: GraphNodeInput[];
  edges: GraphEdgeInput[];
}> = ({ scene, progress }) => {
  const layout = layoutGraph(
    scene.data.nodes,
    scene.data.edges,
    { rankdir: 'TB', nodesep: 36, ranksep: 72 },
  );

  const toSvg = (x: number, y: number) => ({ x: x + 444 - layout.width / 2, y: y + 390 - layout.height / 2 });
  const fade = Math.min(1, Math.max(0, progress * 3));

  return (
    <div style={{ position: 'absolute', left: 0, top: 200, width: 888, height: 1240 }}>
      <div
        style={{
          position: 'absolute',
          left: 48,
          top: 0,
          fontFamily: 'var(--a2v-font)',
          color: 'var(--a2v-accent)',
          fontSize: 44,
          letterSpacing: '0.14em',
        }}
        {...probe({ node: 'graph-kicker', role: 'label' })}
      >
        {scene.data.kicker}
      </div>
      <svg
        width={888}
        height={780}
        style={{ position: 'absolute', left: 0, top: 88, opacity: fade }}
        {...probe({ node: 'graph-canvas', schematic: true })}
      >
        {layout.edges.map((edge) => {
          const points = [edge.points[0], ...edge.points, edge.points[edge.points.length - 1]]
            .filter((point): point is { x: number; y: number } => Boolean(point))
            .map((point) => toSvg(point.x, point.y));
          const path = points
            .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`)
            .join(' ');
          return (
            <path
              key={`${edge.from}-${edge.to}`}
              d={path}
              fill="none"
              stroke="var(--a2v-accent-line)"
              strokeWidth={6}
              strokeDasharray="16 12"
            />
          );
        })}
        {layout.nodes.map((node) => {
          const point = toSvg(node.x, node.y);
          return (
            <g key={node.id}>
              <rect
                x={point.x - node.width / 2}
                y={point.y - node.height / 2}
                width={node.width}
                height={node.height}
                rx={24}
                fill="rgba(255,255,255,0.06)"
                stroke="var(--a2v-accent)"
                strokeWidth={4}
              />
              <text
                x={point.x}
                y={point.y + 16}
                textAnchor="middle"
                fontFamily="var(--a2v-font)"
                fontSize={40}
                fill="var(--a2v-text-1)"
                {...probe({ node: `graph-node-${node.id}`, role: 'label' })}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 48,
          top: 900,
          fontFamily: 'var(--a2v-font)',
          color: 'var(--a2v-text-1)',
          fontSize: 56,
          opacity: fade,
        }}
        {...probe({ node: 'graph-caption', role: 'body' })}
      >
        {scene.data.caption}
      </div>
    </div>
  );
};

export default GraphFlow;
