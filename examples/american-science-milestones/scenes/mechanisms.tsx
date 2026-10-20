/** 按题材绘制轻量、帧确定性的示意动势；不是历史影像或真实数据。 */
export function Mechanism({kind,t,progress,accent}:{kind:string;t:number;progress:number;accent:string}) {
  const sweep=(t*.42)%1;
  const points=Array.from({length:56},(_,i)=>({x:770+(i%8)*122,y:120+Math.floor(i/8)*112,i}));
  if(kind==='wire')return <svg width="920" height="260" viewBox="0 0 920 260" style={{position:'absolute',right:80,top:330,overflow:'visible'}}>
    <path d="M10 145 C220 30 410 250 620 130 S820 65 910 120" fill="none" stroke={accent} strokeWidth="2" opacity=".55"/>
    {Array.from({length:22},(_,i)=>{const x=30+i*39;const active=((t*3.2+i*.32)%6)<.55;return <rect key={i} x={x} y={active?108:108} width={active?25:8} height={active?68:8} rx="2" fill={accent} opacity={active?.9:.36}/>;})}
    <circle cx={10+sweep*900} cy={145+Math.sin(sweep*Math.PI*2)*48} r="10" fill="#fff4db"/>
  </svg>;
  if(kind==='apparatus')return <svg width="1200" height="580" viewBox="0 0 1200 580" style={{position:'absolute',left:500,top:260,overflow:'visible'}}>
    <path d={Array.from({length:121},(_,i)=>`${i?'L':'M'} ${i*10} ${300+Math.sin(i*.29+t*1.9)*80*Math.sin(i/120*Math.PI)}`).join(' ')} fill="none" stroke={accent} strokeWidth="5" opacity=".82"/>
    <path d="M0 300 H1200" fill="none" stroke="#ffffff" strokeWidth="1" opacity=".22"/>
    <circle cx={sweep*1200} cy={300+Math.sin(sweep*Math.PI*2)*70} r="14" fill="#fff1cf"/>
    <text x="42" y="500" fill="#fff" opacity=".75" fontSize="25" letterSpacing="8">声音 → 电信号 → 远方</text>
  </svg>;
  if(kind==='sky')return <svg width="850" height="340" viewBox="0 0 850 340" style={{position:'absolute',right:40,top:160}}>
    <path d="M50 250 Q420 30 800 212" fill="none" stroke="#fff3d9" strokeWidth="2" opacity=".5" strokeDasharray="7 13"/>
    <path d="M90 270 Q400 130 720 228" fill="none" stroke={accent} strokeWidth="3" opacity=".7"/>
    <circle cx={80+progress*680} cy={258-Math.sin(progress*Math.PI)*115} r="8" fill="#fff3d9"/>
  </svg>;
  if(kind==='flash')return <svg width="700" height="700" viewBox="0 0 700 700" style={{position:'absolute',left:650,top:110,opacity:.6}}>
    {[0,1,2,3].map(i=><circle key={i} cx="350" cy="350" r={95+i*90+Math.sin(t*1.8+i)*8} fill="none" stroke={i%2?accent:'#fff1d7'} strokeWidth="2" opacity={.35-i*.045}/>)}
  </svg>;
  if(kind==='machine')return <svg width="1200" height="500" viewBox="0 0 1200 500" style={{position:'absolute',left:460,top:330,opacity:.7}}>
    {Array.from({length:12},(_,i)=><g key={i} opacity={.25+.7*Math.max(0,Math.sin(t*2-i*.42))}><path d={`M${i*94} 40 V440`} stroke={accent} strokeWidth="2"/><circle cx={i*94} cy={80+(i*41)%330} r="8" fill="#fff1d8"/></g>)}
    <path d={`M${sweep*1150} 0 V500`} stroke="#fff1db" strokeWidth="3" opacity=".7"/>
  </svg>;
  if(kind==='silicon')return <svg width="850" height="760" viewBox="0 0 850 760" style={{position:'absolute',right:50,top:120,opacity:.75}}>
    <path d="M80 380 H770 M425 50 V710 M160 115 L690 645 M690 115 L160 645" stroke={accent} strokeWidth="3" opacity=".4"/>
    {Array.from({length:9},(_,i)=><circle key={i} cx={110+i*80} cy={375+Math.sin(i*.8+t*1.4)*120} r={7+(i%3)*2} fill={i===Math.floor(progress*9)%9?'#fff3d9':accent} opacity=".9"/>)}
  </svg>;
  if(kind==='moon')return <div style={{position:'absolute',left:0,right:0,bottom:0,height:190,background:`linear-gradient(0deg,rgba(8,13,17,.85),transparent)`,pointerEvents:'none'}}>
    <div style={{position:'absolute',left:`${10+progress*78}%`,top:40,width:1,height:80,background:'#e9e4d5',opacity:.35}}/>
  </div>;
  if(kind==='map')return <svg width="1050" height="720" viewBox="0 0 1050 720" style={{position:'absolute',left:720,top:160,overflow:'visible'}}>
    <path d="M90 460 L320 180 L620 400 L895 160 M320 180 L895 160 M90 460 L620 400" fill="none" stroke={accent} strokeWidth="3" opacity=".72"/>
    {[[90,460],[320,180],[620,400],[895,160]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r={11+Math.sin(t*2+i)*2} fill="#fff1d9"/>)}
  </svg>;
  if(kind==='sequence')return <svg width="820" height="390" viewBox="0 0 820 390" style={{position:'absolute',right:70,top:220,opacity:.84}}>
    {Array.from({length:25},(_,i)=>{const y=22+i*14,a=t*.75+i*.3,x1=270+Math.sin(a)*95,x2=270-Math.sin(a)*95;return <g key={i}><path d={`M${x1} ${y} Q500 ${y} ${x2} ${y}`} fill="none" stroke={i%2?accent:'#e2d3ad'} strokeWidth="2" opacity=".65"/><circle cx={x1} cy={y} r="4" fill={accent}/><circle cx={x2} cy={y} r="4" fill="#e2d3ad"/></g>;})}
  </svg>;
  if(kind==='language') {
    return <svg width="1120" height="820" viewBox="0 0 1120 820" style={{position:'absolute',right:-30,top:90,opacity:.78}}>
      {points.map(n=>n.i%8<7&&<g key={n.i}><line x1={n.x} y1={n.y} x2={points[n.i+1].x} y2={points[n.i+1].y} stroke={accent} strokeWidth="1.5" opacity=".3"/><line x1={n.x} y1={n.y} x2={points[(n.i+8)%56].x} y2={points[(n.i+8)%56].y} stroke={accent} strokeWidth="1" opacity=".18"/></g>)}
      {points.map(n=><circle key={n.i} cx={n.x} cy={n.y} r={4+3*Math.sin(t*1.1+n.i*.5)**2} fill={n.i%7===Math.floor(progress*7)?'#fff0d4':accent}/>)}
      {[0,1,2].map(i=><circle key={i} cx={800+((progress*900+i*.32)%900)} cy={150+i*200} r="7" fill="#fff4dd"/>)}
    </svg>;
  }
  return null;
}
