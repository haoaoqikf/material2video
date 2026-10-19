/** 辅助原理示意；档案存在时仍保留实物主体，不伪装成历史录像。 */
import {useMemo} from 'react';
import {Chart, echarts} from 'm2v/code-scene';

const nodes = Array.from({length:70},(_,i)=>({x:870+(i%10)*84,y:210+Math.floor(i/10)*74,i}));

/** 电话章节的示意波形：静态数据按帧时钟之外的 ECharts 原生时钟入场，不写历史结论。 */
function TelephoneWave({accent}:{accent:string}) {
  const option = useMemo<echarts.EChartsOption>(() => ({
    animation: true, animationDuration: 1200, animationEasing: 'cubicOut',
    backgroundColor: 'transparent', grid: {left: 0, right: 0, top: 8, bottom: 8},
    xAxis: {type: 'value', show: false, min: 0, max: 200},
    yAxis: {type: 'value', show: false, min: -1, max: 1},
    series: [{type: 'line', showSymbol: false, silent: true, smooth: false,
      lineStyle: {color: accent, width: 2},
      data: Array.from({length:201},(_,i)=>[i, Math.sin(i*.34)*Math.sin(i*.027)])}],
  }), [accent]);
  return <div style={{position:'absolute',left:110,top:700,width:620}}>
    <Chart option={option} width={620} height={90}/>
    <div style={{fontSize:17,color:'#899da6'}}>声音转为电信号 · 波形示意</div>
  </div>;
}

export function Mechanism({kind,t,accent}:{kind:string;t:number;accent:string}) {
  if (kind === 'llm') return <div style={{position:'absolute',left:760,top:170,width:1050,height:630}}>
    <svg width="1050" height="620" viewBox="760 160 1050 620">
      <defs><radialGradient id="halo"><stop stopColor={accent} stopOpacity=".3"/><stop offset="1" stopColor={accent} stopOpacity="0"/></radialGradient></defs>
      <ellipse cx="1330" cy="420" rx="490" ry="300" fill="url(#halo)"/>
      {nodes.map(n=>n.i%10<9 && <g key={n.i}>
        {[0,1,-1].map(d=>{const end=nodes[n.i+1+d*10];if(!end||end.i%10!==(n.i%10)+1)return null;
          const phase=(t*.28+n.i*.039)%1;return <line key={d} x1={n.x} y1={n.y} x2={end.x} y2={end.y}
            stroke={accent} strokeWidth={phase>.65?1.4:.6} opacity={phase>.65?.65:.15}/>;})}</g>)}
      {nodes.map(n=><circle key={n.i} cx={n.x} cy={n.y} r={3+2*Math.sin(t*1.4-n.i*.3)**2}
        fill={accent} opacity={.4+.6*Math.sin(t-n.i*.17)**2}/>)}
      {[0,1,2,3].map(i=><circle key={i} cx={870+((t*.13+i*.25)%1)*755} cy={358+Math.sin(t+i)*45} r="7" fill="#fff2cf"/>)}
    </svg>
    <div style={{position:'absolute',left:60,top:570,fontSize:27,color:'#e1e4dd',letterSpacing:5}}>
      文字输入　→　计算网络　→　生成输出</div>
    <div style={{position:'absolute',left:60,top:625,fontSize:18,color:'#879ea6'}}>原理示意 · 非模型真实内部结构或运行记录</div>
  </div>;
  if (kind==='telegraph') return <svg width="640" height="100" style={{position:'absolute',left:110,top:700}}>
    {Array.from({length:32},(_,i)=><rect key={i} x={i*19} y={40} width={i%3===0?13:4} height="4" fill={accent}
      opacity={((t*.17-i/32+1)%1)>.75?1:.23}/>)}
    <text x="0" y="90" fill="#899da6" fontSize="17">电信号跨越距离 · 摩尔斯编码示意</text>
  </svg>;
  if (kind==='telephone') return <TelephoneWave accent={accent}/>;
  if(kind==='genome') return <svg width="600" height="180" style={{position:'absolute',left:110,top:660}}>
    {Array.from({length:45},(_,i)=>{const a=i*.24+t*.5,y=70+Math.sin(a)*43,z=70-Math.sin(a)*43;
      return <g key={i} opacity={.45+.4*(Math.cos(a)+1)/2}><line x1={i*13} y1={y} x2={i*13} y2={z} stroke={accent}/>
        <circle cx={i*13} cy={y} r="3" fill="#d5c49c"/><circle cx={i*13} cy={z} r="3" fill="#72b2bc"/></g>;})}
    <text x="0" y="165" fill="#899da6" fontSize="17">DNA双螺旋 · 原理示意</text>
  </svg>;
  if(kind==='arpanet') return <svg width="590" height="130" style={{position:'absolute',left:110,top:690}}>
    <path d="M20 70 L180 25 L370 80 L550 30 M180 25 L550 30" fill="none" stroke={accent} opacity=".5"/>
    {[20,180,370,550].map((x,i)=><g key={i}><circle cx={x} cy={[70,25,80,30][i]} r={6+Math.sin(t*2-i)**2*4} fill={accent}/>
      <text x={x-15} y="120" fill="#899da6" fontSize="14">{['UCLA','SRI','UCSB','UTAH'][i]}</text></g>)}
  </svg>;
  return null;
}
