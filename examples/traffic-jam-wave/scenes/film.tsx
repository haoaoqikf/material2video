/**
 * 拥堵波六幕：同一份离线轨迹，按真实旁白时间窗推进。
 *
 * 视觉方向为「夜景俯视道路」：深蓝黑底、冷白车体、橙红制动灯与青色前进标记。
 * 车辆位置、灯态、慢区与图表都从 `traffic.ts` 采样；画面时钟来自录制帧，旁白段只决定
 * 段落与提示的时机。分幕由 `props.mode` 选择，所有场景共用道路、车辆、后视镜与环路零件。
 */
import {useLayoutEffect, useRef, type ReactNode} from 'react';
import {Chart, gsap, type CodeSceneProps} from 'm2v/code-scene';
import {sample, slowCenter, wrapDelta, speedRatio, gapToAhead, gapUnits, loopPoint, TRAFFIC, type CarState, type GroupName} from './traffic';
import {useNarration, useReady} from './stage';

const C = {
  bg: '#050b13', bgTop: '#0a1520', road: '#121b26', edge: '#2e4253', dash: '#7b93a3',
  white: '#f7f4ec', dim: '#8fa4b5', faint: '#5f7281', red: '#ff6b4a', redSoft: '#ff9a82',
  cyan: '#5ad9f0', car: '#d7e6ee', carDark: '#3e5566', glass: '#7fc7d9', tyre: '#070b10',
};
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => {const t = clamp(x); return t * t * (3 - 2 * t);};
const mix = (a: number, b: number, t: number) => a + (b - a) * clamp(t);

function Car({car, x, y, scale = 1.6, focus = false, angle = 0, tag, dim = false, showId = true}: {
  car: CarState; x: number; y: number; scale?: number; focus?: boolean; angle?: number; tag?: string; dim?: boolean;
  showId?: boolean;
}) {
  return <g transform={`translate(${x} ${y})`}>
    <g transform={`rotate(${angle}) scale(${scale})`} opacity={dim ? 0.45 : 1}>
      {focus && <rect x={-38} y={-28} width={76} height={56} rx={16} fill="none" stroke={C.cyan} strokeWidth={2.4}/>}
      <ellipse cx={-2} cy={8} rx={30} ry={13} fill="#000" opacity={0.55}/>
      <path d="M18 -12 L44 -15 L58 -9 L58 9 L44 15 L18 12 Z" fill={C.glass} opacity={0.16}/>
      <rect x={-26} y={-14} width={52} height={28} rx={9} fill={focus ? '#bfeff7' : C.car}/>
      <rect x={-9} y={-11} width={25} height={22} rx={6} fill={C.carDark}/>
      <path d="M9 -11 L16 -9 L16 9 L9 11 Z" fill={C.glass} opacity={0.85}/>
      <rect x={-27} y={-12} width={4} height={24} rx={2} fill={car.brake ? C.red : '#593f3d'}/>
      {car.brake && <rect x={-36} y={-18} width={18} height={36} rx={8} fill={C.red} opacity={0.32} filter="url(#softGlow)"/>}
      <rect x={24} y={-10} width={4} height={6} rx={2} fill={C.white} opacity={0.9}/>
      <rect x={24} y={4} width={4} height={6} rx={2} fill={C.white} opacity={0.9}/>
      <text x={-16} y={4} textAnchor="middle" fontSize={9} fontWeight={700} fill="#0b1520" opacity={showId ? 1 : 0}>{car.id}</text>
    </g>
    {tag && <text x={0} y={-42 * scale} textAnchor="middle" fontSize={13} fontWeight={700} fill={C.cyan}>{tag}</text>}
  </g>;
}

function Road({seconds, y, group = 'high', camera, zoom = 1, focus, height = 320, carScale = 1.6,
  showIds = true, slowLabel = false, tagId, dim = false}: {
  seconds: number; y: number; group?: GroupName; camera?: number; zoom?: number; focus?: number;
  height?: number; carScale?: number; showIds?: boolean; slowLabel?: boolean; tagId?: number; dim?: boolean;
}) {
  const cars = sample(group, seconds);
  const ref = camera ?? (slowCenter(cars) ?? cars[0].s);
  const placed = cars.map(car => ({car, x: 540 + wrapDelta(car.s, ref) * zoom}))
    .filter(item => item.x > -120 && item.x < 1200)
    .sort((a, b) => (a.car.id === focus ? 1 : 0) - (b.car.id === focus ? 1 : 0));
  const slows = placed.filter(item => speedRatio(item.car.speed) < TRAFFIC.thresholds.slowRatio);
  const band = slows.length
    ? {left: Math.min(...slows.map(item => item.x)) - 86, right: Math.max(...slows.map(item => item.x)) + 86}
    : null;
  const dashOffset = ((ref * zoom) % 170 + 170) % 170;
  return <g>
    <rect x={-40} y={y - height / 2} width={1160} height={height} fill="url(#roadPaint)"/>
    <path d={`M-40 ${y - height / 2}H1120 M-40 ${y + height / 2}H1120`} stroke={C.edge} strokeWidth={3}/>
    <path d={`M-40 ${y - height / 2 + 10}H1120 M-40 ${y + height / 2 - 10}H1120`} stroke={C.edge} strokeWidth={1} opacity={0.5}/>
    {Array.from({length: 10}, (_, i) => {
      const x = -170 + i * 170 + dashOffset;
      return <path key={i} d={`M${x} ${y}h64`} stroke={C.dash} strokeWidth={3} opacity={0.28}/>;
    })}
    {Array.from({length: 8}, (_, i) => {
      const x = -120 + i * 170 + dashOffset;
      return <g key={`post-${i}`} opacity={0.5}>
        <path d={`M${x} ${y - height / 2 - 12}v12 M${x} ${y + height / 2}v12`} stroke={C.faint} strokeWidth={2}/>
      </g>;
    })}
    {band && <>
      <rect x={band.left} y={y - height / 2 + 22} width={band.right - band.left} height={height - 44} rx={70}
        fill="url(#slowBand)" opacity={0.56}/>
      <path d={`M${band.left + 12} ${y - height / 2 + 22}H${band.right - 12}`} stroke={C.red} strokeWidth={2} opacity={0.55} strokeDasharray="10 8"/>
      {slowLabel && <text x={(band.left + band.right) / 2} y={y - height / 2 - 18} textAnchor="middle" fontSize={26}
        fontWeight={700} fill={C.red}>慢区</text>}
    </>}
    {placed.map(({car, x}) => <g key={car.id}>
      <path d={`M${x + 16 * carScale} ${y - 8}L${x + 92 * carScale} ${y - 34}V${y + 34}L${x + 16 * carScale} ${y + 8}Z`}
        fill={C.white} opacity={0.07}/>
      <Car car={car} x={x} y={y} scale={carScale} focus={car.id === focus}
        tag={car.id === tagId ? '你' : undefined} dim={dim} showId={showIds}/>
    </g>)}
  </g>;
}

function Ring({seconds, scale = .85, y = 850, focus}: {seconds: number; scale?: number; y?: number; focus?: number}) {
  const cars = sample('high', seconds);
  const slow = cars.filter(car => speedRatio(car.speed) < TRAFFIC.thresholds.slowRatio);
  const reference = slow.length ? slow[0].s : 0;
  const deltas = slow.map(car => wrapDelta(car.s, reference));
  const from = Math.min(...deltas) - 40;
  const to = Math.max(...deltas) + 40;
  const points = slow.length > 1
    ? Array.from({length: 28}, (_, i) => loopPoint(reference + from + (to - from) * i / 27))
    : [];
  const polyline = points.map((point, i) => `${i ? 'L' : 'M'}${point.x} ${point.y}`).join(' ');
  return <g transform={`translate(540 ${y}) scale(${scale})`}>
    <ellipse rx={TRAFFIC.loop.rx + 82} ry={TRAFFIC.loop.ry + 82} fill="#0b141e" opacity={0.85}/>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke={C.edge} strokeWidth={108}/>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke={C.road} strokeWidth={102}/>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke={C.dash} strokeWidth={2}
      strokeDasharray="18 34" opacity={0.35}/>
    {polyline && <path d={polyline} fill="none" stroke={C.red} strokeWidth={128} strokeLinecap="round" opacity={0.22}/>}
    {slow.map(car => <circle key={car.id} cx={car.x} cy={car.y} r={80} fill={C.red} opacity={0.16}/>)}
    {cars.map(car => <Car key={car.id} car={car} x={car.x} y={car.y} angle={car.heading * 180 / Math.PI}
      scale={1.35} focus={car.id === focus} tag={car.id === focus ? '8 号车' : undefined}/>)}
  </g>;
}

function Arrow({x1, x2, y, color, opacity = 1, label, width = 6}: {
  x1: number; x2: number; y: number; color: string; opacity?: number; label?: string; width?: number;
}) {
  const left = x2 < x1;
  const head = left ? `M${x2} ${y}l${26} -15v30z` : `M${x2} ${y}l-26 -15v30z`;
  return <g opacity={opacity}>
    <path d={`M${x1} ${y}H${x2}`} stroke={color} strokeWidth={width} strokeLinecap="round"/>
    <path d={head} fill={color}/>
    {label && <text x={(x1 + x2) / 2} y={y - 22} textAnchor="middle" fontSize={30} fontWeight={700} fill={color}>{label}</text>}
  </g>;
}

function Mirror({seconds, x, y, w, h, scale = 1, label = '后视镜', focus = 8}: {
  seconds: number; x: number; y: number; w: number; h: number; scale?: number; label?: string; focus?: number;
}) {
  const cars = sample('high', seconds);
  const camera = slowCenter(cars) ?? cars[focus - 1].s;
  return <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <rect x={-8} y={-8} width={w + 16} height={h + 16} rx={30} fill="#02070c" stroke={C.edge} strokeWidth={3}/>
    <svg x={0} y={0} width={w} height={h} viewBox="0 0 1080 300" preserveAspectRatio="xMidYMid slice">
      <Road seconds={seconds} y={150} height={260} zoom={0.42} carScale={0.95} focus={focus}
        camera={camera} showIds={false}/>
    </svg>
    <rect x={0} y={0} width={w} height={h} fill="url(#mirrorGlass)" opacity={0.5}/>
    <text x={18} y={-18} fontSize={22} fontWeight={700} fill={C.dim} letterSpacing={2}>{label}</text>
  </g>;
}

function Title({top, left = 76, size = 78, color = C.white, opacity = 1, weight = 750, children, width}: {
  top: number; left?: number; size?: number; color?: string; opacity?: number; weight?: number;
  children: ReactNode; width?: number;
}) {
  return <div style={{position: 'absolute', left, top, width, fontSize: size, fontWeight: weight,
    lineHeight: 1.18, letterSpacing: 1, color, opacity}}>{children}</div>;
}

function Label({top, left = 76, size = 30, color = C.dim, opacity = 1, children}: {
  top: number; left?: number; size?: number; color?: string; opacity?: number; children: ReactNode;
}) {
  return <div style={{position: 'absolute', left, top, fontSize: size, color, opacity, lineHeight: 1.45}}>{children}</div>;
}

function City() {
  return <g opacity={0.55}>
    {Array.from({length: 14}, (_, i) => {
      const x = (i * 197) % 1040 - 40;
      const y = (i * 311) % 1760 - 40;
      const w = 90 + (i * 37) % 110;
      const h = 60 + (i * 53) % 150;
      return <g key={i}>
        <rect x={x} y={y} width={w} height={h} rx={6} fill="#0c1824"/>
        <rect x={x + 8} y={y + 8} width={w - 16} height={h - 16} rx={3} fill="#0a141e" stroke="#142433" strokeWidth={1}/>
        {Array.from({length: Math.max(2, Math.floor(h / 34))}, (_, row) =>
          <path key={row} d={`M${x + 12} ${y + 20 + row * 30}h${Math.max(12, w - 24)}`} stroke="#21384a" strokeWidth={2} opacity={0.7}/>)}
      </g>;
    })}
  </g>;
}

const curve = (group: GroupName, from: number, to: number): [number, number][] => {
  const count = Math.max(2, Math.min(80, Math.round((to - from) * 8) + 2));
  return Array.from({length: count}, (_, i) => {
    const seconds = from + (to - from) * i / (count - 1);
    return [Number((seconds - 7).toFixed(2)), Math.round(speedRatio(sample(group, seconds)[5].speed) * 100)];
  });
};

export default function Film(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const t = clock.elapsedSeconds;
  const mode = String(props.props.mode ?? 'empty');
  const duration = props.durationInFrames / props.fps;
  const sceneProgress = clamp(t / Math.max(0.001, duration));
  const span = (ids: string[]) => {
    const first = props.segmentWindows[ids[0]];
    const last = props.segmentWindows[ids[ids.length - 1]];
    if (!first || !last) return 0;
    const from = first.startFrame / props.fps;
    const to = last.endFrame / props.fps;
    return clamp((t - from) / Math.max(0.001, to - from));
  };
  const at = (id: string) => (props.segmentWindows[id] ? clock.progress(id) : 0);
  const reveal = (id: string, speed = 5) => Math.min(1, at(id) * speed);

  const emptyTime = 18 + span(['e1', 'e2']) * 0.8;
  const mirrorTime = 18 + span(['e1', 'e2']) * 0.8;
  const rewindTime = 7.5 + span(['w1', 'w2']) * 7.5;
  const brakeTime = 7 + span(['b1', 'b2']) * 5.5;
  const relayTime = 7 + span(['l1', 'l2', 'l3']) * 14;
  const densityTime = 7 + span(['d1', 'd2']) * 11;
  const returnTime = 19 + span(['f1', 'f2', 'f3']) * 2.2;
  const rewindAnchor = sample('high', 7)[0].s + TRAFFIC.groups.high.spacing * 2;
  const brakeAnchor = sample('high', 7)[0].s + TRAFFIC.groups.high.spacing * 2.4;
  const brakeZoom = mix(0.72, 0.88, ease(t / 2.2));
  const ringScale = mix(0.74, 0.86, ease(t / 5));
  const chartReveal = ease((t - 4.2) / 1.6);
  const mirrorReveal = ease((t - duration * 0.62) / 1.4);
  const emptyReveal = reveal('e1', 4);
  const returnReveal = reveal('f2', 3);
  const sourceReveal = reveal('f3', 3);

  // 红色反向箭头由帧时间驱动 GSAP 补间；不使用挂钟，重复录制逐帧一致。
  const arrow = useRef<SVGGElement>(null);
  useLayoutEffect(() => {
    if (!arrow.current) return;
    const appear = clamp((t - 1.4) / 1.2);
    gsap.set(arrow.current, {opacity: appear, x: 34 * (1 - appear)});
  }, [t]);

  const chart = {
    animation: false, backgroundColor: 'transparent',
    grid: {left: 58, right: 30, top: 30, bottom: 46},
    textStyle: {color: C.dim, fontSize: 21, fontFamily: 'Noto Sans SC'},
    xAxis: {type: 'value', min: 0, max: 12, axisLabel: {color: C.dim, fontSize: 20}, splitLine: {show: false}},
    yAxis: {type: 'value', min: 0, max: 100, axisLabel: {color: C.dim, fontSize: 20, formatter: '{value}%'},
      splitLine: {lineStyle: {color: '#1d2f3d'}}},
    series: [
      {type: 'line', data: curve('high', 7, densityTime), showSymbol: false, lineStyle: {color: C.red, width: 5}},
      {type: 'line', data: curve('low', 7, densityTime), showSymbol: false, lineStyle: {color: C.cyan, width: 5}},
    ],
  };

  return <div style={{width: props.width, height: props.height, position: 'relative', overflow: 'hidden',
    background: `radial-gradient(ellipse at 50% 30%, ${C.bgTop} 0%, ${C.bg} 62%)`, color: C.white,
    fontFamily: 'Noto Sans SC, sans-serif'}}>
    <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
      <defs>
        <linearGradient id="roadPaint" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#16222f"/><stop offset="0.5" stopColor="#121b26"/><stop offset="1" stopColor="#0c141e"/>
        </linearGradient>
        <linearGradient id="slowBand" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor={C.red} stopOpacity="0"/><stop offset="0.18" stopColor={C.red} stopOpacity="0.34"/>
          <stop offset="0.82" stopColor={C.red} stopOpacity="0.34"/><stop offset="1" stopColor={C.red} stopOpacity="0"/>
        </linearGradient>
        <linearGradient id="mirrorGlass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#dff7ff" stopOpacity="0.22"/><stop offset="0.45" stopColor="#dff7ff" stopOpacity="0.03"/>
          <stop offset="1" stopColor="#000" stopOpacity="0.16"/>
        </linearGradient>
        <filter id="softGlow"><feGaussianBlur stdDeviation="6"/></filter>
      </defs>
      <City/>
      {mode === 'empty' && <>
        <Road seconds={emptyTime} y={900} height={330} zoom={0.92} carScale={1.55} focus={8} tagId={8} slowLabel
          camera={sample('high', emptyTime)[7].s - TRAFFIC.groups.high.spacing * 2.2}/>
        <Mirror seconds={mirrorTime} x={676} y={128} w={330} h={238} scale={1} focus={8}/>
      </>}
      {mode === 'rewind' && <>
        <Road seconds={rewindTime} y={810} height={380} zoom={0.55} carScale={1.4} camera={rewindAnchor}
          focus={8} slowLabel tagId={8}/>
        <g ref={arrow}><Arrow x1={920} x2={170} y={1040} color={C.red} width={7} label="慢区向后"/></g>
        <Arrow x1={160} x2={930} y={590} color={C.cyan} width={6} label="车流向前"/>
      </>}
      {mode === 'brake' && <>
        <g>
          {Array.from({length: 6}, (_, i) => {
            const x = 150 + i * 150;
            const active = speedRatio(sample('high', brakeTime)[i].speed) < TRAFFIC.thresholds.brakeRatio;
            return <g key={i}>
              <circle cx={x} cy={430} r={16} fill={active ? C.red : '#1d2f3d'} stroke={active ? C.redSoft : C.edge}
                strokeWidth={2} opacity={active ? 0.95 : 0.8}/>
              <text x={x} y={472} textAnchor="middle" fontSize={18} fill={active ? C.red : C.dim}>{i + 1}</text>
            </g>;
          })}
          <path d="M126 396H954" stroke={C.edge} strokeWidth={2} opacity={0.8}/>
          <text x={540} y={360} textAnchor="middle" fontSize={22} fill={C.dim}>每辆车的反应，晚 0.85 秒</text>
        </g>
        <Road seconds={brakeTime} y={850} height={370} zoom={brakeZoom} carScale={1.55} camera={brakeAnchor}
          focus={1}/>
      </>}
      {mode === 'relay' && <>
        <Ring seconds={relayTime} scale={ringScale} y={880} focus={8}/>
      </>}
      {mode === 'density' && <>
        <Road seconds={densityTime} y={560} height={190} zoom={0.5} carScale={1.2} group="high"
          camera={sample('high', 7)[0].s + TRAFFIC.groups.high.spacing * 8}/>
        <Road seconds={densityTime} y={860} height={190} zoom={0.5} carScale={1.2} group="low"
          camera={sample('high', 7)[0].s + TRAFFIC.groups.high.spacing * 8}/>
      </>}
      {mode === 'return' && <>
        <Road seconds={returnTime} y={900} height={330} zoom={0.92} carScale={1.55} focus={8} tagId={8} slowLabel
          camera={sample('high', returnTime)[7].s - TRAFFIC.groups.high.spacing * 2.2}/>
        <Mirror seconds={returnTime} x={666} y={118} w={340} h={250} scale={0.98 + mirrorReveal * 0.16} focus={8}/>
      </>}
    </svg>

    {mode === 'empty' && <>
      <Label top={86} size={24} color={C.cyan}>你刚驶出拥堵</Label>
      <Title top={138} size={72} width={590}>堵了半天，</Title>
      <Title top={228} size={72} width={590} opacity={emptyReveal}>前面<span style={{color: C.red}}>什么都没有</span>？</Title>
      <Label top={1110} size={34} color={C.cyan} opacity={reveal('e1', 3)}>前方畅通，没有事故，也没有封路。</Label>
      <Label top={1170} size={30} color={C.red} opacity={reveal('e2', 3)}>可后视镜里，还是一片红灯。</Label>
      <Label top={1450} size={22} color={C.faint}>预设示意 · 非实测</Label>
    </>}
    {mode === 'rewind' && <>
      <Label top={84} size={22} color={C.dim}>回放 · 00:{rewindTime.toFixed(1).padStart(4, '0')}</Label>
      <Title top={136} size={78} width={860}>拥堵，在往后跑。</Title>
      <Label top={248} size={32} color={C.cyan} opacity={reveal('w2', 4)}>车在往前开</Label>
      <Label top={294} size={32} color={C.red} opacity={reveal('w2', 4)}>慢下来的区域，却在往后退</Label>
      <Label top={1130} size={28} color={C.dim}>同一段时间里，两个方向同时发生。</Label>
      <div style={{position: 'absolute', left: 76, top: 1210, width: 928, height: 8, borderRadius: 4, background: '#172838'}}>
        <div style={{width: `${Math.round(sceneProgress * 100)}%`, height: 8, borderRadius: 4,
          background: `linear-gradient(90deg, ${C.cyan}, ${C.red})`}}/>
      </div>
    </>}
    {mode === 'brake' && <>
      <Label top={84} size={22} color={C.dim}>局部放大 · 预设轨迹</Label>
      <Title top={136} size={66} width={928}>一切从一次轻刹车开始。</Title>
      <Label top={252} size={32} color={C.dim} opacity={reveal('b1', 4)}>前车减速，后车没法同时反应。</Label>
      <Label top={1120} size={34} color={C.red} opacity={reveal('b2', 3)}>一辆接一辆，刹车灯向后亮起。</Label>
      <Label top={1188} size={26} color={C.dim}>1 号车与后车：{gapUnits(gapToAhead(sample('high', brakeTime), 1)).toFixed(1)} 车位</Label>
      <Label top={1450} size={22} color={C.faint}>反应延迟 0.85 秒/辆 · 预设模型</Label>
    </>}
    {mode === 'relay' && <>
      <Label top={84} size={22} color={C.dim}>没有路口 · 没有出口 · 没有事故</Label>
      <Title top={136} size={80} width={860}>换的是车，<span style={{color: C.red}}>不是路。</span></Title>
      <div style={{position: 'absolute', left: 300, top: 812, width: 480, textAlign: 'center',
        fontSize: 44, fontWeight: 750, lineHeight: 1.35}}>
        同一团拥堵<br/><span style={{color: C.red}}>不同的车</span>
      </div>
      <Label top={1400} size={30} color={C.cyan} opacity={reveal('l2', 3)}>蓝框车一直向前，红色慢区不断换车。</Label>
      <Label top={1450} size={22} color={C.faint}>环路全景 · 预设示意</Label>
    </>}
    {mode === 'density' && <>
      <div style={{position: 'absolute', right: 76, top: 86, fontSize: 22, color: C.dim,
        border: `2px solid ${C.edge}`, borderRadius: 999, padding: '6px 16px'}}>补充解释</div>
      <Title top={136} size={62} width={900}>同样的刹车，两种结果。</Title>
      <Label top={400} size={30} color={C.red}>密集车流 · 响应放大</Label>
      <Label top={700} size={30} color={C.cyan}>稀疏车流 · 逐渐减弱</Label>
      <Label top={1000} size={22} color={C.dim}>第 6 辆车 · 相对速度</Label>
      <div style={{position: 'absolute', left: 64, top: 1030, width: 960, height: 390, opacity: chartReveal,
        transform: `translateY(${18 * (1 - chartReveal)}px)`}}>
        <Chart option={chart} width={960} height={390}/>
      </div>
      <Label top={1452} size={22} color={C.faint} opacity={reveal('d2', 4)}>预设模型 · 非实测 · 仅解释一种机制</Label>
    </>}
    {mode === 'return' && <>
      <Label top={84} size={24} color={C.cyan}>回到那条路</Label>
      <Title top={136} size={78} width={560}>你穿过的，</Title>
      <Title top={228} size={78} width={560} opacity={returnReveal}>是一道<span style={{color: C.red}}>拥堵波</span>。</Title>
      <Label top={1110} size={32} color={C.white} opacity={returnReveal}>车继续向前，波留在身后。</Label>
      <Label top={1180} size={28} color={C.dim} opacity={returnReveal}>所以堵了半天却什么都没看见，并不奇怪。</Label>
      <Label top={1400} size={24} color={C.dim} opacity={sourceReveal}>原创示意动画 · 机制依据：杉山等，2008</Label>
      <Label top={1444} size={22} color={C.faint} opacity={sourceReveal}>预设模型，非实测；仅解释拥堵的一种机制。</Label>
    </>}
  </div>;
}
