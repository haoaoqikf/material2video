/**
 * 数据：把同一段过程画成三条线——输入、输出与箱内积压。
 *
 * 示意数据按守恒关系算出：每段最多输出 4 个单位，先有 8 个单位存量，
 * 输入超过 4 积压增加，低于 4 积压减少。第二段旁白开口后补上输出上限与守恒标注。
 */
import {useMemo} from 'react';
import {Chart, echarts, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, useNarration, useReady} from './stage';

//: 每段输入（示意），刻意高低交替：缓冲关心的是这种不整齐。
const INPUT = [7, 3, 8, 2, 6, 3, 7, 4, 6, 3];
const CAPACITY_PER_STEP = 4;
const START_BACKLOG = 8;

/** 按守恒关系推积压与输出：输出只截到上限，差额全部进积压。 */
export function ledger(input: number[] = INPUT) {
  let backlog = START_BACKLOG;
  const stock: number[] = [];
  const output: number[] = [];
  for (const value of input) {
    const drained = Math.min(backlog + value, CAPACITY_PER_STEP);
    backlog = backlog + value - drained;
    stock.push(backlog);
    output.push(drained);
  }
  return {stock, output};
}

export default function Flow(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const detailed = clock.spoken('buffer-flow-1');
  const option = useMemo(() => chartOption(detailed), [detailed]);
  const chart = {width: props.width - 440, height: contentBottom(props) - 330};

  return (
    <Stage props={props} title="流量与积压，要一起看"
      note={`每段最多输出 ${CAPACITY_PER_STEP} 个单位，先有 ${START_BACKLOG} 个单位存量`}>
      <div style={{position: 'absolute', left: 220, top: 300}}>
        <Chart option={option} width={chart.width} height={chart.height}/>
      </div>
    </Stage>
  );
}

function chartOption(detailed: boolean): echarts.EChartsOption {
  const {stock, output} = ledger();
  const axis = {axisLine: {lineStyle: {color: COLOR.rule}}, axisLabel: {color: COLOR.muted}, splitLine: {lineStyle: {color: COLOR.grid}}};
  return {
    backgroundColor: 'transparent',
    animationDuration: 1400,
    grid: {left: 96, right: 96, top: 60, bottom: 64},
    legend: {textStyle: {color: COLOR.muted, fontSize: SIZE.note}, top: 0, left: 'center'},
    tooltip: {show: false},
    xAxis: {type: 'category', data: INPUT.map((_, index) => `${index + 1}`), name: '时段', nameTextStyle: {color: COLOR.muted}, ...axis},
    yAxis: [
      {type: 'value', name: '份/秒', nameTextStyle: {color: COLOR.muted}, ...axis},
      {type: 'value', name: '积压', nameTextStyle: {color: COLOR.muted}, ...axis},
    ],
    series: [
      {name: '输入', type: 'line', data: INPUT, smooth: false, symbolSize: 8,
        lineStyle: {color: COLOR.accent, width: 4}, itemStyle: {color: COLOR.accent}},
      {name: '输出', type: 'line', data: output, symbolSize: 8,
        lineStyle: {color: COLOR.warn, width: 4}, itemStyle: {color: COLOR.warn},
        ...(detailed ? {markLine: {silent: true, symbol: 'none', label: {color: COLOR.warn, formatter: '输出上限 4'},
          lineStyle: {color: COLOR.warn, type: 'dashed'}, data: [{yAxis: CAPACITY_PER_STEP}]}} : {})},
      {name: '积压', type: 'bar', yAxisIndex: 1, data: stock, barWidth: 26,
        itemStyle: {color: COLOR.rule}, opacity: 0.9},
    ],
  };
}
