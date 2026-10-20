/**
 * 对照：同样的道路、初速和 1 号车的刹车，只改变车流密度。
 *
 * 两条直路是同一条环路展开后的局部路段，镜头跟着 1 号车。红色与蓝色速度曲线
 * 由同一份采样数据直接生成：高密度下游响应被放大，低密度逐渐恢复。
 * 这是原理示意，不是受控实验，也不宣称密度是任何条件下的唯一原因。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {Chart} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, useNarration, useReady} from './stage';
import {CarMark, StraightRoad} from './parts';
import {type GroupName, TRAFFIC, sample, slowCenter, speedRatio, wrapDelta} from './traffic';

const HIGH_BAND = {y: 376, height: 252};
const LOW_BAND = {y: 704, height: 252};
const SCALE = 0.78;
const CHART = {left: 96, top: 1032, width: 888, height: 392};
const PROBE = 5; // 第 6 辆车：两组取相同序号，方便比较响应

const curve = (group: GroupName): [number, number][] =>
  Array.from({length: 161}, (_, index) => {
    const t = index / 10;
    const cars = sample(group, TRAFFIC.disturbance.start + t);
    return [Number(t.toFixed(1)), Math.round(speedRatio(cars[PROBE].speed) * 100)];
  });

const OPTION = {
  backgroundColor: 'transparent',
  animation: false,
  grid: {left: 64, right: 92, top: 22, bottom: 46},
  textStyle: {fontFamily: 'Noto Sans SC, Inter, sans-serif', fontSize: 17, color: COLOR.muted},
  xAxis: {
    type: 'value', min: 0, max: 16, name: '秒', nameLocation: 'end', nameGap: 12,
    axisLine: {lineStyle: {color: COLOR.edge}}, axisTick: {show: false},
    splitLine: {show: false}, axisLabel: {fontSize: 16},
  },
  yAxis: {
    type: 'value', min: 0, max: 110, name: '相对速度 %', nameGap: 14,
    axisLine: {show: false}, axisTick: {show: false},
    splitLine: {lineStyle: {color: COLOR.rule, type: 'dashed'}}, axisLabel: {fontSize: 16},
  },
  series: [
    {
      name: '高密度', type: 'line', showSymbol: false, smooth: false, data: curve('high'),
      lineStyle: {width: 3.5, color: COLOR.brake},
      endLabel: {show: true, formatter: '高密度', color: COLOR.brake, fontSize: 17, fontWeight: 700,
        offset: [0, -16]},
    },
    {
      name: '低密度', type: 'line', showSymbol: false, smooth: false, data: curve('low'),
      lineStyle: {width: 3.5, color: COLOR.accent},
      endLabel: {show: true, formatter: '低密度', color: COLOR.accent, fontSize: 17, fontWeight: 700,
        offset: [0, 14]},
    },
  ],
} as const;

export default function Density(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const sim = TRAFFIC.disturbance.start + clock.elapsedSeconds;
  const high = sample('high', sim);
  const low = sample('low', sim);
  // 两段使用同一观察窗口：镜头跟着高密度组的低速区域，低密度组在同一段路上展开。
  const camera = slowCenter(high) ?? high[0].s;

  return (
    <Stage props={props} title="同样的刹车，只改变车流密度"
      lead="两条直路是同一条环路的同一段，取同一时刻">
      <Band label="高密度" count={TRAFFIC.groups.high.cars} y={HIGH_BAND.y} height={HIGH_BAND.height}
        cars={high} camera={camera} tone={COLOR.brake}/>
      <Band label="低密度" count={TRAFFIC.groups.low.cars} y={LOW_BAND.y} height={LOW_BAND.height}
        cars={low} camera={camera} tone={COLOR.accent}/>

      <div style={{position: 'absolute', left: 96, top: 986, right: 96, display: 'flex',
        justifyContent: 'space-between', alignItems: 'baseline'}}>
        <span style={{fontSize: SIZE.body, fontWeight: 700}}>第 6 辆车的相对速度</span>
        <span style={{fontSize: SIZE.note, color: COLOR.muted}}>同一扰动条件 · 曲线为示意采样</span>
      </div>
      <div style={{position: 'absolute', left: CHART.left, top: CHART.top, width: CHART.width,
        height: CHART.height, background: COLOR.paper, border: `2px solid ${COLOR.rule}`,
        borderRadius: 14, overflow: 'hidden'}}>
        <Chart option={OPTION} width={CHART.width} height={CHART.height}/>
      </div>
      <div style={{position: 'absolute', left: 96, top: contentBottom(props) - 18, right: 96,
        fontSize: SIZE.note, color: COLOR.muted, display: 'flex', justifyContent: 'space-between'}}>
        <span>两条曲线都从 100% 巡航速度出发</span>
        <span>高密度：响应放大。低密度：扰动消散。</span>
      </div>
    </Stage>
  );
}

function Band({label, count, y, height, cars, camera, tone}: {
  label: string; count: number; y: number; height: number;
  cars: ReturnType<typeof sample>; camera: number; tone: string;
}) {
  const center = y + height / 2;
  return (
    <div style={{position: 'absolute', left: 96, top: y - 44, right: 96, display: 'flex',
      justifyContent: 'space-between', alignItems: 'center'}}>
      <span style={{fontSize: SIZE.body, fontWeight: 700, color: tone}}>{`${label} · ${count} 辆`}</span>
      <span style={{fontSize: SIZE.note, color: COLOR.muted}}>同一时刻</span>
      <svg width={1080} height={height} style={{position: 'absolute', left: -96, top: 44}}>
        <StraightRoad width={1080} y={0} height={height} cameraS={camera * SCALE} center={540}/>
        {cars.map(car => {
          const dx = wrapDelta(car.s, camera) * SCALE;
          if (Math.abs(dx) > 610) return null;
          return <CarMark key={car.id} x={540 + dx} y={center - y} heading={0} braking={car.brake}
            label={car.id} scale={0.82}
            opacity={0.25 + 0.75 * Math.max(0, 1 - Math.abs(dx) / 610)}/>;
        })}
        <text x={540} y={22} textAnchor="middle" fontSize={SIZE.note} fill={COLOR.muted}
          opacity={0.85}>同一段环路</text>
      </svg>
    </div>
  );
}
