import {useEffect, useMemo} from 'react';
import {motion, Chart, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

const input = [8, 2, 7, 1, 6, 2, 5, 1];
// 初始存量 8、服务上限 4，输出和积压由守恒关系计算。
const samples = input.reduce<{output: number[]; stock: number[]}>((result, incoming) => {
  const available = (result.stock.at(-1) ?? 8) + incoming;
  const outgoing = Math.min(4, available);
  result.output.push(outgoing); result.stock.push(available-outgoing);
  return result;
}, {output: [], stock: []});

export default function BufferDemo({props, fps, segmentWindows, theme}: CodeSceneProps) {
  const {ready, elapsedSeconds, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  const windows = Object.values(segmentWindows).sort((a,b)=>a.startFrame-b.startFrame);
  const frame = elapsedSeconds*fps;
  const ratio = (w: typeof windows[number]) => w ? Math.max(0, Math.min(1,(frame-w.startFrame)/Math.max(1,w.endFrame-w.startFrame))) : 0;
  const phase = windows[1] && frame >= windows[1].startFrame ? 1 : 0;
  const level = phase === 0 ? 0.25+ratio(windows[0])*0.5 : 0.75-ratio(windows[1])*0.5;
  const ink = theme === 'light' ? '#172434' : '#edf4fc';
  const muted = theme === 'light' ? '#526174' : '#a9b9cb';
  const step = Math.min(8,Math.floor((phase+ratio(windows[phase]))*4)+1);
  const option = useMemo(() => ({
    animation: false, textStyle: {fontFamily: 'Noto Sans SC',color: ink,fontSize: 23},
    legend: {top: 8,textStyle: {color: ink,fontSize: 25},data: ['输入','输出','积压']},
    grid: [{left: 65,right: 40,top: 80,height: 285},{left: 65,right: 40,top: 465,height: 225}],
    xAxis: [0,1].map(gridIndex=>({type: 'category' as const,gridIndex,data: input.map((_,i)=>`${i+1}`),axisLabel: {color: muted,fontSize: 23},name: '时段'})),
    yAxis: [0,1].map(gridIndex=>({type: 'value' as const,gridIndex,min: 0,max: gridIndex ? 16 : 10,interval: gridIndex ? 4 : 2,axisLabel: {color: muted,fontSize: 23},splitLine: {lineStyle: {color: '#52617444'}},name: gridIndex ? '积压单位' : '每段流量'})),
    series: [
      {name: '输入',type: 'line' as const,data: input.slice(0,step),lineStyle: {width: 5},itemStyle: {color: '#5aafff'},symbolSize: 12},
      {name: '输出',type: 'line' as const,data: samples.output.slice(0,step),lineStyle: {width: 5},itemStyle: {color: '#f7c85b'},symbolSize: 12},
      {name: '积压',type: 'bar' as const,xAxisIndex: 1,yAxisIndex: 1,data: samples.stock.slice(0,step),itemStyle: {color: '#68cdb5'},barWidth: 40},
    ],
  }), [step,ink,muted]);
  return <div style={{height: 920,color: ink,fontSize: 32,fontFamily: 'Noto Sans SC'}}>
    {props.view === 'chart' ? <>
      <Chart option={option} height={760}/>
      <div style={{padding: '12px 36px',color: muted}}>初始存量 8 · 每段最多输出 4</div>
      <div style={{padding: '0 36px',fontSize: 27}}>流量与容量均为示意单位</div>
    </> : <>
      <motion.div initial={{opacity: 0,y: 12}} animate={{opacity: running ? 1 : 0,y: running ? 0 : 12}} style={{padding: '30px 44px',fontSize: 38}}>
        {phase ? '入口变慢，存水补上' : '入口加速，多余先存'}
      </motion.div>
      <svg width="864" height="650" viewBox="0 0 864 650" aria-label="水箱积存与释放示意">
        <defs><clipPath id="tank"><rect x="232" y="160" width="400" height="410" rx="18"/></clipPath></defs>
        <path d="M110 95H310V165" stroke="#5aafff" strokeWidth="30" fill="none"/>
        <path d="M630 500H760" stroke="#f7c85b" strokeWidth="28" fill="none"/>
        <g clipPath="url(#tank)"><rect x="232" y={570-410*level} width="400" height={410*level} fill="#3b9ee3"/>
          {[0,1,2].map(i=><circle key={i} cx={290+i*130} cy={phase ? 490 : 195+(elapsedSeconds*85+i*90)%310} r="10" fill="#a4dfff"/>)}</g>
        <rect x="232" y="160" width="400" height="410" rx="18" stroke={ink} strokeWidth="5" fill="none"/>
        <text x="68" y="55" fill="#5aafff" fontSize="32">波动输入</text>
        <text x="620" y="610" fill="#f7c85b" fontSize="32">稳定取水</text>
        <text x="432" y="350" textAnchor="middle" fill={ink} fontSize="42">{phase ? '存量减少' : '存量增加'}</text>
      </svg>
      <div style={{textAlign: 'center',color: muted}}>有存水、留空位，才能承接波动</div>
      <div style={{textAlign: 'center',marginTop: 25,fontSize: 27}}>水位与流速仅作机制示意</div>
    </>}
  </div>;
}
