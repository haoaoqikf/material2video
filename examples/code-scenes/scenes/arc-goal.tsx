import { frameStroke, probe, type A2VCodeScene } from '@a2v/scene';

/**
 * 定制 SVG 示例：圆环进度由 progress 驱动 stroke-dashoffset，
 * 不用 CSS transition/animation——描边只跟帧号走。
 */
const ArcGoal: A2VCodeScene<{ kicker: string; caption: string; percent: number }> = ({
  scene,
  progress,
}) => {
  const radius = 260;
  const circumference = 2 * Math.PI * radius;
  const draw = Math.min(1, Math.max(0, progress * 1.4));
  const dash = frameStroke(draw, circumference);
  const percentText = `${Math.round(scene.data.percent * 100)}%`;

  return (
    <div style={{ position: 'absolute', left: 0, top: 360, width: 1080, height: 1200 }}>
      <div
        style={{
          position: 'absolute',
          left: 96,
          top: 0,
          fontFamily: 'var(--a2v-font)',
          color: 'var(--a2v-accent)',
          fontSize: 44,
          letterSpacing: '0.14em',
        }}
        {...probe({ node: 'arc-kicker', role: 'label' })}
      >
        {scene.data.kicker}
      </div>
      <svg
        width={1080}
        height={760}
        style={{ position: 'absolute', left: 0, top: 160 }}
        {...probe({ node: 'arc-canvas', schematic: true })}
      >
        <circle
          cx={540}
          cy={380}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.10)"
          strokeWidth={36}
        />
        <circle
          cx={540}
          cy={380}
          r={radius}
          fill="none"
          stroke="var(--a2v-accent)"
          strokeWidth={36}
          strokeLinecap="round"
          // pathLength 声明周长后，dash 值直接用像素周长计算
          pathLength={circumference}
          strokeDasharray={dash.dasharray}
          strokeDashoffset={dash.offset}
          transform="rotate(-90 540 380)"
        />
        <text
          x={540}
          y={380 - 10}
          textAnchor="middle"
          fontFamily="var(--a2v-font)"
          fontSize={160}
          fontWeight={700}
          fill="var(--a2v-text-1)"
          {...probe({ node: 'arc-percent', role: 'hero' })}
        >
          {percentText}
        </text>
        <text
          x={540}
          y={380 + 96}
          textAnchor="middle"
          fontFamily="var(--a2v-font)"
          fontSize={48}
          fill="var(--a2v-line)"
          {...probe({ node: 'arc-note', role: 'caption' })}
        >
          已完成
        </text>
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 96,
          top: 960,
          fontFamily: 'var(--a2v-font)',
          color: 'var(--a2v-text-1)',
          fontSize: 60,
          opacity: Math.min(1, Math.max(0, progress * 2 - 0.6)),
        }}
        {...probe({ node: 'arc-caption', role: 'body' })}
      >
        {scene.data.caption}
      </div>
    </div>
  );
};

export default ArcGoal;
