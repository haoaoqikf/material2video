import { frameStyle, probe, useFrameChart, type A2VCodeScene } from '@a2v/scene';

/**
 * ECharts 示例：逐帧 option 由 progress 驱动，图表实例随组件挂载/卸载。
 * 动画强制关闭（useFrameChart 内置），柱体长度只跟帧号走。
 */
const ProgressChart: A2VCodeScene<{
  kicker: string;
  caption: string;
  labels: string[];
  values: number[];
}> = ({ scene, progress }) => {
  const revealed = scene.data.values.map((value) => Math.round(value * Math.min(1, progress * 1.6)));
  const chart = useFrameChart(
    () => ({
      xAxis: { type: 'category', data: scene.data.labels },
      yAxis: { type: 'value', max: 100, splitLine: { show: false } },
      grid: { left: 72, right: 48, top: 48, bottom: 72 },
      series: [
        {
          type: 'bar',
          data: revealed,
          barWidth: 96,
          itemStyle: { color: 'var(--a2v-accent)', borderRadius: 12 },
          label: { show: true, position: 'top', color: 'var(--a2v-text-1)', fontSize: 32 },
        },
      ],
    }),
    [scene.data.labels, revealed],
  );

  return (
    <div style={{ position: 'absolute', left: 0, top: 400, width: 1080, height: 1080 }}>
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
        {...probe({ node: 'chart-kicker', role: 'label' })}
      >
        {scene.data.kicker}
      </div>
      <div
        ref={chart.ref}
        style={{ position: 'absolute', left: 0, top: 110, width: 1080, height: 800 }}
        {...probe({ node: 'chart-canvas', schematic: true })}
      />
      <div
        style={{
          position: 'absolute',
          left: 96,
          top: 940,
          fontFamily: 'var(--a2v-font)',
          color: 'var(--a2v-text-1)',
          fontSize: 56,
          ...frameStyle(Math.min(1, Math.max(0, progress * 2)), { opacity: true }),
        }}
        {...probe({ node: 'chart-caption', role: 'body' })}
      >
        {scene.data.caption}
      </div>
    </div>
  );
};

export default ProgressChart;
