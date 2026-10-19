/** 辅助原理示意；档案存在时仍保留实物主体，不伪装成历史录像。 */
import {useMemo} from 'react';
import {Chart, echarts} from 'm2v/code-scene';

/** 电报章节的信号带：符号按帧时钟依次点亮，不表示真实报文内容。 */
export function MorsePulse({t, accent}: {t: number; accent: string}) {
  return <svg width={940} height={112} style={{position:'absolute',left:120,top:648,overflow:'visible'}}>
    {Array.from({length:38},(_,i)=>{
      const on = (t * .42 - i * .04 + 1) % 1 < .16;
      const width = i % 4 === 0 ? 24 : 9;
      return <rect key={i} x={i * 24} y={30} width={width} height={5} rx={2.5}
        fill={accent} opacity={on ? .95 : .18}/>;
    })}
    {Array.from({length:38},(_,i)=><line key={'grid' + i} x1={i * 24} x2={i * 24} y1={22} y2={42}
      stroke="#ffffff10"/>)}
    <line x1={0} y1={52} x2={920} y2={52} stroke="#ffffff12"/>
    <text x={0} y={86} fill="#8fa0a8" fontSize={24} letterSpacing={2}>电信号 · 摩尔斯编码示意</text>
  </svg>;
}

/** 电话章节的波形：静态数据按 ECharts 原生时钟入场，不写历史结论。 */
export function TelephoneWave({accent}: {accent: string}) {
  const option = useMemo<echarts.EChartsOption>(() => ({
    animation: true, animationDuration: 1100, animationEasing: 'cubicOut',
    backgroundColor: 'transparent', grid: {left: 0, right: 0, top: 6, bottom: 6},
    xAxis: {type: 'value', show: false, min: 0, max: 200},
    yAxis: {type: 'value', show: false, min: -1, max: 1},
    series: [{type: 'line', showSymbol: false, silent: true, smooth: false,
      lineStyle: {color: accent, width: 1.8},
      data: Array.from({length: 201}, (_, i) => [i, Math.sin(i * .31) * Math.sin(i * .021)])}],
  }), [accent]);
  return <div style={{position:'absolute',left:120,top:620,width:860}}>
    <Chart option={option} width={860} height={126}/>
    <div style={{fontSize:24,color:'#8fa0a8',marginTop:2,letterSpacing:2}}>声音转为电信号 · 波形示意</div>
  </div>;
}

/** 晶体管截面示意：发射极—基极—集电极与按帧移动的载流子。 */
export function TransistorDiagram({t, accent}: {t: number; accent: string}) {
  const x = 170, w = 340;
  const layers = [
    {y: 40, h: 96, label: '发射极'},
    {y: 146, h: 32, label: '基极'},
    {y: 188, h: 96, label: '集电极'},
  ];
  return <svg width={760} height={470} style={{position:'absolute',left:1060,top:170}}>
    <defs>
      <linearGradient id="transistor-body" x1="0" y1="0" x2="1" y2="0">
        <stop stopColor="#203638"/><stop offset=".5" stopColor="#2d4a4c"/><stop offset="1" stopColor="#192b2e"/>
      </linearGradient>
    </defs>
    {layers.map((layer, i) => <g key={layer.label}>
      <rect x={x} y={layer.y} width={w} height={layer.h} rx={6}
        fill={i === 1 ? '#b79a64' : 'url(#transistor-body)'}
        stroke={i === 1 ? '#e3ca92' : accent} strokeOpacity={.55}/>
      <text x={x + w + 26} y={layer.y + layer.h / 2 + 7} fill="#d9dfda"
        fontSize={24}>{layer.label}</text>
    </g>)}
    <path d={`M ${x + w / 2} 300 L ${x + w / 2} 380`} stroke={accent} strokeWidth={2}
      strokeDasharray="4 6" opacity=".55"/>
    {Array.from({length:9},(_,i)=>{
      const phase = (t * .6 + i / 9) % 1;
      return <circle key={i} cx={x + w / 2 + Math.sin(i * 2.1) * 50} cy={40 + phase * 244}
        r={4.5} fill="#ffe8b8" opacity={phase < .72 ? .9 : .12}/>;
    })}
    <path d={`M ${x - 78} 300 L ${x - 18} 300`} stroke={accent} strokeWidth={2}/>
    <path d={`M ${x + w + 178} 236 L ${x + w + 18} 236`} stroke={accent} strokeWidth={2}/>
    <text x={x - 84} y={288} fill="#8fa0a8" fontSize={24} textAnchor="end">电流</text>
    <text x={x + w + 190} y={222} fill="#8fa0a8" fontSize={24}>输出</text>
    <line x1={x} y1={336} x2={x + w} y2={336} stroke="#ffffff14"/>
    <text x={x} y={404} fill="#8fa0a8" fontSize={24} letterSpacing={2}>点接触晶体管 · 原理示意</text>
  </svg>;
}

const ARPA_NODES = [
  {x: 78, y: 82, name: 'UCLA'},
  {x: 300, y: 40, name: 'SRI'},
  {x: 548, y: 88, name: 'UCSB'},
  {x: 360, y: 168, name: 'UTAH'},
];
const ARPA_LINKS = [[0, 1], [0, 2], [1, 2], [2, 3]] as const;

/** 独立的初始四节点示意；不叠加在档案图上，避免与图内旧标签混淆。 */
export function ArpanetNodes({t, accent}: {t: number; accent: string}) {
  return <svg width={700} height={250} style={{position:'absolute',left:120,top:590,pointerEvents:'none'}}>
    {ARPA_LINKS.map(([a, b], k) => {
      const from = ARPA_NODES[a], to = ARPA_NODES[b];
      const phase = (t * .55 + k * .21) % 1;
      return <g key={k}>
        <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={accent}
          strokeWidth={1.4} opacity={.42}/>
        <circle cx={from.x + (to.x - from.x) * phase} cy={from.y + (to.y - from.y) * phase}
          r={4.5} fill="#ffe8b8" opacity={.92}/>
      </g>;
    })}
    {ARPA_NODES.map((node, i) => <g key={node.name}>
      <circle cx={node.x} cy={node.y} r={8 + Math.sin(t * 2.2 + i) * 2} fill={accent} opacity={.9}/>
      <circle cx={node.x} cy={node.y} r={19} fill="none" stroke={accent} opacity={.28}/>
      <text x={node.x} y={node.y + 40} fill="#dbe3e0" fontSize={22}
        textAnchor="middle" letterSpacing={2}>{node.name}</text>
    </g>)}
    <text x={0} y={238} fill="#8fa0a8" fontSize={24} letterSpacing={2}>初始四节点 · 示意</text>
  </svg>;
}

/** 基因组章节的双螺旋叠加层：只作结构示意。 */
export function GenomeHelix({t, accent}: {t: number; accent: string}) {
  return <svg width={280} height={720} style={{position:'absolute',left:1610,top:100,opacity:.95}}>
    {Array.from({length:44},(_,i)=>{
      const angle = i * .31 + t * .65, y = 18 + i * 14;
      const x1 = 140 + Math.sin(angle) * 62, x2 = 140 - Math.sin(angle) * 62;
      const depth = (Math.cos(angle) + 1) / 2;
      return <g key={i}>
        <line x1={x1} y1={y} x2={x2} y2={y} stroke={accent} strokeWidth={1.5}
          opacity={.18 + .4 * depth}/>
        <circle cx={x1} cy={y} r={3.8} fill="#dccda4" opacity={.4 + .6 * depth}/>
        <circle cx={x2} cy={y} r={3.8} fill="#7cc0c4" opacity={.4 + .6 * (1 - depth)}/>
      </g>;
    })}
    <text x={0} y={690} fill="#8fa0a8" fontSize={24} letterSpacing={2}>DNA双螺旋 · 原理示意</text>
  </svg>;
}

/** 大模型章节的抽象计算网络：输入、层间传递与输出，明确不是真实模型记录。 */
export function LLMNetwork({t, accent}: {t: number; accent: string}) {
  const cols = 9, rows = 6;
  const nodeX = (column: number) => 90 + column * 118;
  const nodeY = (row: number) => 60 + row * 86;
  return <svg width={1180} height={640} style={{position:'absolute',left:560,top:110}}>
    <defs>
      <radialGradient id="llm-halo">
        <stop stopColor={accent} stopOpacity=".26"/><stop offset="1" stopColor={accent} stopOpacity="0"/>
      </radialGradient>
    </defs>
    <ellipse cx={562} cy={280} rx={540} ry={300} fill="url(#llm-halo)"/>
    {Array.from({length:cols - 1},(_,column)=>Array.from({length:rows},(_,row)=>{
      const x1 = nodeX(column), y1 = nodeY(row);
      return [-1, 0, 1].map(offset => {
        const target = row + offset;
        if (target < 0 || target >= rows) return null;
        const phase = (t * .45 + column * .09 + row * .07 + offset * .11) % 1;
        return <line key={`${column}-${row}-${offset}`} x1={x1} y1={y1}
          x2={nodeX(column + 1)} y2={nodeY(target)} stroke={accent}
          strokeWidth={phase > .72 ? 1.6 : .8} opacity={phase > .72 ? .62 : .17}/>;
      });
    }))}
    {Array.from({length:cols},(_,column)=>Array.from({length:rows},(_,row)=>{
      const pulse = .35 + .65 * Math.sin(t * 1.6 - column * .4 - row * .3) ** 2;
      const fill = column < 3 ? '#dccda4' : column > 6 ? '#8fd0d2' : accent;
      return <circle key={`${column}-${row}`} cx={nodeX(column)} cy={nodeY(row)}
        r={3.6 + 2.4 * pulse} fill={fill} opacity={.36 + .6 * pulse}/>;
    }))}
    {Array.from({length:6},(_,i)=>{
      const phase = (t * .32 + i * .17) % 1;
      return <circle key={'packet' + i} cx={nodeX(0) + phase * (nodeX(cols - 1) - nodeX(0))}
        cy={nodeY(2) + Math.sin(t * 1.2 + i * 1.7) * 70} r={5.5}
        fill="#fff1c9" opacity={.9}/>;
    })}
    <line x1={90} y1={30} x2={1034} y2={30} stroke="#ffffff12"/>
    <text x={90} y={20} fill="#8fa0a8" fontSize={20} letterSpacing={4}>输入</text>
    <text x={1034} y={20} fill="#8fa0a8" fontSize={20} letterSpacing={4} textAnchor="end">输出</text>
  </svg>;
}
