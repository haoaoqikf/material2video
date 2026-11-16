import {clamp01, ease} from './components/kit';

const nodes = [
  {x:175,y:433,label:'UCLA',dy:78},
  {x:524,y:242,label:'SRI',dy:-48},
  {x:154,y:196,label:'UCSB',dy:-48},
  {x:982,y:139,label:'UTAH',dy:-48},
] as const;
// 1969 年末的三角形与接到 SRI 的犹他节点，位置仅作布局。
const links = [[0,1], [1,2], [0,2], [1,3]] as const;

export function Network({chapter, frame, events}: {
  chapter:{year:string; title:string; caption:string; alias?:string};
  frame:number;
  events:Readonly<Record<string,number>> | undefined;
}) {
  const progress = links.map((_,index) => {
    const start = events?.[`link-${index+1}`];
    return start === undefined ? 0 : ease((frame-start)/13);
  });
  const connectedNodes = nodes.map((_,index)=>links.some(([a,b],i)=>(a===index||b===index)&&progress[i]>=1));
  const connectedCount = connectedNodes.filter(Boolean).length;
  const finished = connectedCount === nodes.length;
  const caption = connectedCount === 0 ? '四个节点等待接通' : `已接通 ${connectedCount} 个节点`;
  return <main style={{
    position:'absolute', inset:0, overflow:'hidden', color:'#29251c',
    background:'radial-gradient(ellipse at 71% 21%,#fbebca,#d2af7f 92%)',
  }}>
    <div style={{position:'absolute', left:122, top:300, width:560}}>
      <div style={{fontSize:42, letterSpacing:3, color:'#735031'}}>{chapter.year}</div>
      <h1 style={{fontSize:104, fontWeight:640, lineHeight:1.08, margin:'16px 0 12px'}}>{chapter.title}</h1>
      <div style={{fontSize:33, letterSpacing:4, color:'#735031'}}>{chapter.alias}</div>
      <p style={{fontSize:49, lineHeight:1.23, margin:'27px 0 0'}}>{finished ? chapter.caption : caption}</p>
    </div>
    <svg viewBox="0 0 1160 650" width="1160" height="650" role="img" aria-label="1969 年末的阿帕网四节点关系"
      style={{position:'absolute', right:98, top:215, filter:'drop-shadow(0 8px 7px #51341d4a)'}}>
      <defs>
        <linearGradient id="copper-wire" x1="12%" y1="5%" x2="36%" y2="100%">
          <stop stopColor="#a15730"/>
          <stop offset=".4" stopColor="#d28a57"/>
          <stop offset="1" stopColor="#663318"/>
        </linearGradient>
        <linearGradient id="copper-terminal" x1="15%" y1="0" x2="80%" y2="100%">
          <stop stopColor="#f4cb8b"/>
          <stop offset=".55" stopColor="#b56e40"/>
          <stop offset="1" stopColor="#69351d"/>
        </linearGradient>
      </defs>
      {links.map(([a,b],i) => {
        const {x,y}=nodes[a], {x:x2,y:y2}=nodes[b];
        const p=progress[i];
        if (p === 0) return null;
        const tipX=x+(x2-x)*p, tipY=y+(y2-y)*p;
        return <g key={i}>
          <line x1={x} y1={y} x2={tipX} y2={tipY} stroke="#5d301a" strokeWidth="15" strokeLinecap="round"/>
          <line x1={x} y1={y-2} x2={tipX} y2={tipY-2} stroke="url(#copper-wire)" strokeWidth="9" strokeLinecap="round"/>
          {p<1 && <circle cx={tipX} cy={tipY} r="10" fill="#ebbd78" stroke="#6f3b22" strokeWidth="3"/>}
        </g>;
      })}
      {nodes.map(({x,y,label,dy},index) => {
        const active = connectedNodes[index];
        return <g key={label}>
          <circle cx={x} cy={y} r="30" fill="#e8d0a1" stroke="#9b7146" strokeWidth="3"/>
          <circle cx={x} cy={y} r="21" fill={active?'url(#copper-terminal)':'#f2e1bd'} stroke="#693b23" strokeWidth="4"/>
          <circle cx={x} cy={y} r="7" fill={active?'#63351c':'#b68e5a'}/>
          <text x={x} y={y+dy} textAnchor="middle" fill="#34271d" fontSize="43" fontWeight="680">{label}</text>
        </g>;
      })}
    </svg>
    <div style={{position:'absolute', right:126, bottom:111, color:'#513720', fontSize:41}}>
      {finished ? '1969 年末拓扑示意' : '接通过程示意'} · DARPA / UCLA
    </div>
  </main>;
}

export function BaseSequence({progress}: {progress:number}) {
  return <div style={{
    position:'absolute', left:121, top:518, color:'#ecf0dd', opacity:clamp01(progress),
    textShadow:'0 2px 16px #131914',
  }}>
    <div style={{fontSize:43, color:'#d6e1cb', marginBottom:13}}>碱基序列示意</div>
    <div style={{fontSize:66, letterSpacing:11, fontWeight:600, lineHeight:1}}>A G C T T A G C</div>
    {/* 保留真实底片的读数区域，连接线止于其左边缘。 */}
    <div aria-hidden style={{
      position:'absolute', top:160, left:0, width:672, height:5,
      background:'linear-gradient(90deg,#829c8055,#d6ead0)',
    }}>
      <div style={{
        position:'absolute', left:'100%', top:0, width:359, height:5,
        background:'#d6ead0', boxShadow:'0 2px 4px #142422',
        transform:'rotate(-29deg)', transformOrigin:'left',
      }}>
        <div style={{
          position:'absolute', left:'100%', top:'50%', width:18, height:18,
          border:'4px solid #d6ead0', borderRadius:'50%', boxShadow:'0 1px 5px #142422',
          transform:'translate(-50%,-50%)',
        }}/>
      </div>
    </div>
  </div>;
}
