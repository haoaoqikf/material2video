import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {
  FIRST_DISC_INDEX, Disc, Text, BG, DARK_GOLD, GOLD, MUTED, OFF_WHITE,
  columnPositions, hillPositions, mixColor, shelfPositions,
} from './discs';
import {
  clamp, discDiameter, discFractions, ease, money, segmentAt, withdrawState, yearAt, yearState,
} from './compoundMath';

const RIGHT_X = 1420;
const LEFT_X = 700;
const HILL_CENTER = 1360;
const BASE_Y = 900;
const PITCH = 28;
const TOP10 = BASE_Y - 9 * PITCH;        // 648
const FIRST_GOLD_Y = 590;
const GOLD_REST = 586;
const NEW_GOLD_Y = 558;

const leftColumn = columnPositions(LEFT_X, BASE_Y, 10, PITCH);
const rightColumn = columnPositions(RIGHT_X, BASE_Y, 13, PITCH);
const shelf = shelfPositions(30, 300, 400);
const hill = hillPositions(159);
// 与数学精确对应：158.631 枚米白（含 0.631）与 15.863 枚金，不再丢掉零头。
const hillUnits = discFractions(yearState(30).offWhiteUnits);
const finalGold = discFractions(yearState(30).goldUnits);
const goldRow = finalGold.map((unit, i) => ({
  x: HILL_CENTER + (i - (finalGold.length - 1) / 2) * 40,
  y: hill[FIRST_DISC_INDEX].y - 48, unit,
}));
// S4 结束时的 12 枚米白 + 第 3 年已转为资本的那枚。第 11 枚（下标 10）是第一年的收益，
// 在丘上固定映射到顶行中央，供 S6 回扣。
const PRE_TARGETS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, FIRST_DISC_INDEX, 10, 11];
const PRE_SOURCES = [...rightColumn.slice(0, 12), {x: RIGHT_X, y: NEW_GOLD_Y}];
const RAIN_TARGETS = hill.map((_, i) => i).filter(i => !PRE_TARGETS.includes(i));
// 落点顺序打散：金雨应像随机落下，而不是从左到右扫过。
const RAIN_ORDER = [...RAIN_TARGETS].sort((a, b) =>
  ((Math.sin(a * 12.9898) * 43758.5453) % 1) - ((Math.sin(b * 12.9898) * 43758.5453) % 1));

type Cam = {x: number; y: number; s: number};
const CAM_KEYS: {t: number; cam: Cam}[] = [
  {t: 0, cam: {x: 960, y: 540, s: 1}},
  {t: 3.65, cam: {x: 960, y: 540, s: 1}},
  {t: 4.65, cam: {x: RIGHT_X, y: 740, s: 2.5}},
  {t: 8.0, cam: {x: RIGHT_X, y: 740, s: 2.5}},
  {t: 12.2, cam: {x: RIGHT_X, y: 740, s: 2.5}},
  {t: 13.4, cam: {x: 960, y: 540, s: 1.05}},
  {t: 18.8, cam: {x: 960, y: 540, s: 1.05}},
  {t: 19.6, cam: {x: 960, y: 540, s: 1}},
  {t: 24.0, cam: {x: 960, y: 540, s: 1}},
  {t: 24.8, cam: {x: 1360, y: 702, s: 2.4}},
  {t: 27.0, cam: {x: 1360, y: 702, s: 2.4}},
  {t: 29.6, cam: {x: 960, y: 540, s: 1}},
  {t: 30.0, cam: {x: 960, y: 540, s: .985}},
];

function cameraAt(t: number): Cam {
  let index = 0;
  while (index < CAM_KEYS.length - 2 && t > CAM_KEYS[index + 1].t) index++;
  const from = CAM_KEYS[index], to = CAM_KEYS[index + 1];
  const p = ease((t - from.t) / Math.max(1e-6, to.t - from.t));
  return {x: from.cam.x + (to.cam.x - from.cam.x) * p,
    y: from.cam.y + (to.cam.y - from.cam.y) * p,
    s: Math.exp(Math.log(from.cam.s) + (Math.log(to.cam.s) - Math.log(from.cam.s)) * p)};
}

const arrive = (t: number, at: number, duration = .5) => ease((t - at) / duration);
const dropAt = (i: number) => .55 + i * .09;

function StartColumns({t}: {t: number}) {
  return <>
    {[LEFT_X, RIGHT_X].map(x => columnPositions(x, BASE_Y, 10, PITCH).map((p, i) => {
      const land = dropAt(i);
      const p1 = clamp((t - (land - .45)) / .45);
      const bounce = t > land ? Math.sin((t - land) * 17) * 7 * Math.exp(-(t - land) * 7) : 0;
      return <Disc key={`${x}-${i}`} x={p.x} y={-60 + (p.y + 60) * ease(p1) + bounce}
        opacity={clamp((t - (land - .45)) / .18)}/>;
    }))}
  </>;
}

function RightColumn({t}: {t: number}) {
  if (t < 8) {
    const grow = ease((t - 4.2) / .9);
    const float = ease((t - 5.2) / 1.4);
    const settle = ease((t - 6.6) / .8);
    const gy = 618 - 40 * float + 12 * settle;
    return <>
      {rightColumn.slice(0, 10).map((p, i) => <Disc key={`r${i}`} x={p.x} y={p.y}/>)}
      {grow > 0 && <g transform={`rotate(${30 * float} ${RIGHT_X} ${gy})`}>
        <Disc x={RIGHT_X} y={gy} r={21 * grow} state="gold"/>
      </g>}
    </>;
  }
  if (t < 13) {
    const ret = ease((t - 8) / 1.0);
    const pulse = t > 9.4 && t < 10.6 ? Math.sin((t - 9.4) * Math.PI / .6) : 0;
    const grow = ease((t - 10.2) / .9);
    const rim = ret > .95 ? GOLD : undefined;
    return <>
      {rightColumn.slice(0, 10).map((p, i) => <Disc key={`r${i}`} x={p.x}
        y={p.y - 4 * Math.sin(i * .9 + t * 6) * pulse}/>)}
      <Disc x={RIGHT_X} y={FIRST_GOLD_Y + (rightColumn[10].y - FIRST_GOLD_Y) * ret}
        state="white" color={mixColor(GOLD, OFF_WHITE, ret)} rim={rim}/>
      {grow > 0 && <>
        <Disc x={RIGHT_X} y={GOLD_REST + 54 * (1 - grow)} r={21 * grow} state="gold"/>
        <Disc x={RIGHT_X + 30} y={GOLD_REST + 54 * (1 - grow)}
          r={21 * Math.sqrt(.1) * grow} state="gold"/>
      </>}
    </>;
  }
  if (t < 19) {
    const commit = ease((t - 15.2) / 1.0);
    const merge = ease((t - 15.2) / .8);
    const grow = ease((t - 16.0) / .9);
    const shelfIn = ease((t - 12.6) / .6);
    return <>
      {rightColumn.slice(0, 11).map((p, i) => <Disc key={`r${i}`} x={p.x} y={p.y}/>)}
      <Disc x={RIGHT_X} y={GOLD_REST + 6 * commit}
        state="white" color={mixColor(GOLD, OFF_WHITE, commit)} rim={commit > .95 ? GOLD : undefined}/>
      <Disc x={RIGHT_X + 30 * (1 - merge)} y={GOLD_REST + 6 * commit}
        r={21 * Math.sqrt(.1)} state="white" color={mixColor(GOLD, OFF_WHITE, commit)}
        opacity={1 - merge}/>
      {grow > 0 && <Disc x={RIGHT_X} y={NEW_GOLD_Y + 40 * (1 - grow)} r={21 * grow} state="gold"/>}
      {shelfIn > 0 && shelf.slice(0, 2).map((p, i) => <Disc key={`pre${i}`} x={p.x}
        y={p.y - 60 * (1 - shelfIn)} state="dark" opacity={shelfIn}/>)}
    </>;
  }
  return null;
}

function LeftGroup({t}: {t: number}) {
  if (t < 13) {
    return <>{leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x} y={p.y}/>)}</>;
  }
  if (t < 19) {
    const appear = ease((t - 13.6) / .5);
    const fly = ease((t - 14.2) / 1.0);
    const target = shelf[2];
    const x = LEFT_X + (target.x - LEFT_X) * fly;
    const y = (TOP10 - 40) + (target.y - (TOP10 - 40)) * fly - Math.sin(fly * Math.PI) * 90;
    return <>
      {leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x} y={p.y}/>)}
      {shelf.slice(0, 2).map((p, i) => <Disc key={`pre${i}`} x={p.x} y={p.y} state="dark"/>)}
      {appear > 0 && <Disc x={x} y={y} state="gold" opacity={appear}
        color={mixColor(GOLD, DARK_GOLD, fly)} rim={t < 15.2 ? GOLD : undefined}/>}
    </>;
  }
  const lift = ease((t - 19) / .8);
  const sourceX = 730 + 30 * lift;
  const sourceY = 430 + 200 * (1 - lift);
  return <>
    {leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x + 30 * lift} y={p.y - 200 * lift}/>)}
    {shelf.map((p, i) => {
      if (i < 3) return <Disc key={`s${i}`} x={p.x} y={p.y} state="dark"/>;
      const land = 19.3 + 2.1 * Math.pow(i / 29, .8);
      if (t < land - .35) return null;
      const drop = ease(clamp((t - (land - .35)) / .35));
      const x = sourceX + (p.x - sourceX) * drop;
      const y = sourceY + (p.y - sourceY) * drop - Math.sin(drop * Math.PI) * 40;
      return <Disc key={`s${i}`} x={x} y={y} state="dark" opacity={clamp((t - (land - .35)) / .2)}/>;
    })}
  </>;
}

function Sweep({t}: {t: number}) {
  const p = clamp((t - 27) / 3);
  const x = -600 + 2600 * p;
  return <>
    <rect x={x} y={-200} width={380} height={1500} fill="url(#sweep)" opacity={.10}
      transform="skewX(-16)"/>
    {Array.from({length: 14}, (_, i) => {
      const dx = ((Math.sin(i * 12.9898) * 43758.5453) % 1) * 1000 + 600;
      const dy = 760 - (t - 27) * (8 + (i % 5) * 2) - ((i * 37) % 180);
      return <circle key={`d${i}`} cx={dx} cy={dy} r={1.6 + (i % 3) * .6}
        fill={OFF_WHITE} opacity={.18 + (i % 4) * .05}/>;
    })}
  </>;
}

function Hill({t}: {t: number}) {
  const dim = 1 - .85 * arrive(t, 24, .8) * (1 - arrive(t, 27, 1.2));
  const tremble = t > 26.4 ? Math.sin((t - 26.4) * 36) * 3 * Math.exp(-(t - 26.4) * 5) : 0;
  const spread = ease((t - 19) / .8);
  const floatOut = arrive(t, 24.8, .8) * (1 - arrive(t, 25.8, .8));
  const back = arrive(t, 25.8, .8);
  const goldFlash = Math.sin(clamp((t - 25.1) / 1.1) * Math.PI);
  const firstColor = mixColor(OFF_WHITE, GOLD, goldFlash);
  const lift = arrive(t, 28, 1);
  return <>
    {PRE_TARGETS.map((targetIndex, i) => {
      const target = hill[targetIndex], source = PRE_SOURCES[i];
      const isFirst = targetIndex === FIRST_DISC_INDEX;
      const committing = targetIndex === PRE_TARGETS[12];
      const x = source.x + (target.x - source.x) * spread;
      const y = source.y + (target.y - source.y) * spread + tremble;
      return <Disc key={`p${i}`} x={x} y={isFirst ? y - 70 * floatOut + 6 * back : y}
        state="white" color={isFirst ? firstColor : committing ? mixColor(GOLD, OFF_WHITE, spread) : undefined}
        rim={isFirst && t >= 24 ? GOLD : undefined}
        opacity={isFirst ? 1 : dim}/>;
    })}
    {RAIN_ORDER.map((targetIndex, i) => {
      const p = hill[targetIndex], unit = hillUnits[targetIndex];
      const land = 19.7 + 1.7 * Math.pow(i / Math.max(1, RAIN_ORDER.length - 1), .62);
      const fall = clamp((t - (land - .35)) / .35);
      if (t < land - .35) return null;
      const rim = t > land && t < land + 1 ? GOLD : undefined;
      return <Disc key={`h${targetIndex}`} x={p.x} y={p.y - 340 * (1 - ease(fall)) + tremble}
        r={discDiameter(unit) / 2} state="white" color={mixColor(GOLD, OFF_WHITE, fall)}
        rim={rim} opacity={dim}/>;
    })}
    {goldRow.map((g, i) => {
      const land = 21.0 + i * .025;
      const p = ease(clamp((t - land) / .35));
      if (t < land) return null;
      const highlight = i === 7 ? lift : 0;
      const start = {x: hill[FIRST_DISC_INDEX].x, y: hill[FIRST_DISC_INDEX].y - 48};
      return <Disc key={`g${i}`} x={start.x + (g.x - start.x) * p}
        y={start.y + (g.y - start.y) * p - Math.sin(p * Math.PI) * 24 - 10 * highlight}
        r={discDiameter(g.unit) / 2} state="gold" rim={highlight > .2 ? OFF_WHITE : undefined}
        opacity={dim}/>;
    })}
    {t >= 27 && <Sweep t={t}/>}
  </>;
}

function YearLabel({t}: {t: number}) {
  if (t < 13 || t >= 24) return null;
  // S5 时间快进段不逐格报年份，避免与“从第3年到第30年”的标题抢读；21.5秒落定第30年。
  if (t >= 19 && t < 21.4) return null;
  return <Text x={1800} y={155} size={62} color={GOLD} anchor="end" weight={600}>第 {yearAt(t)} 年</Text>;
}

function TextLayer({t}: {t: number}) {
  const segment = segmentAt(t);
  const footnote = arrive(t, 4.4, .5) * (1 - arrive(t, 24.0, .5));
  // 开场标签在S2推近的头0.35秒内淡出，避免镜头移动时标签与柱脱开。
  const approach = arrive(t, 1.35, .35) * (1 - arrive(t, 3.5, .15));
  return <>
    {approach > 0 && <>
      <Text x={LEFT_X} y={610} size={48} anchor="middle" opacity={approach}>收益取走</Text>
      <Text x={RIGHT_X} y={610} size={48} color={GOLD} anchor="middle" opacity={approach}>收益再投入</Text>
    </>}
    {segment === 'S1' && <>
      <Text x={120} y={170} size={76} weight={600}>同样一万</Text>
      <Text x={120} y={262} size={76} weight={600}>两种做法</Text>
      <Text x={120} y={360} size={60} color={MUTED} opacity={arrive(t, 2.2, .4)}>三十年后差多少？</Text>
    </>}
    {segment === 'S2' && <>
      <Text x={120} y={75} size={44} color={GOLD}
        opacity={arrive(t, 3.55, .15)}>收益再投入</Text>
      <Text x={120} y={150} size={66} weight={600}>第 1 年</Text>
      <Text x={120} y={230} size={48} color={MUTED}>10,000 × 10% = <tspan fill={GOLD}>1,000</tspan></Text>
    </>}
    {segment === 'S3' && <>
      <Text x={120} y={75} size={44} color={GOLD}
        opacity={arrive(t, 3.55, .15)}>收益再投入</Text>
      <Text x={120} y={150} size={66} weight={600}>第 2 年</Text>
      <Text x={120} y={230} size={48} color={MUTED}>11,000 × 10% = <tspan fill={GOLD}>1,100</tspan></Text>
    </>}
    {segment === 'S4' && <>
      <Text x={510} y={300} size={56} weight={600} anchor="middle">收益取走</Text>
      <Text x={510} y={350} size={52} color={MUTED} anchor="middle">拿走，不再生息</Text>
      <Text x={1360} y={300} size={56} weight={600} anchor="middle">收益再投入</Text>
      <Text x={1360} y={350} size={52} color={MUTED} anchor="middle">留在里面，继续生息</Text>
      <Text x={1360} y={445} size={64} color={MUTED} anchor="middle"
        opacity={arrive(t, 15.2, .4)}>12,100 × 10% = 1,210</Text>
    </>}
    {segment === 'S5' && <>
      <Text x={120} y={140} size={46} color={MUTED}>同样的 10,000，同样的 10%</Text>
      <Text x={120} y={195} size={60} color={MUTED}>{t < 21.4 ? '从第 3 年，到第 30 年' : '30 年累计总额（元）'}</Text>
      <Text x={572} y={270} size={52} weight={600} anchor="middle">收益取走 · 合计</Text>
      <Text x={1360} y={270} size={52} weight={600} anchor="middle">收益再投入 · 合计</Text>
      <Text x={572} y={350} size={84} anchor="middle" weight={600}
        opacity={arrive(t, 21.4, .2)}>{money(withdrawState(30).total)}</Text>
      <Text x={1360} y={350} size={88} color={GOLD} anchor="middle" weight={600}
        opacity={arrive(t, 21.4, .2)}>{money(yearState(30).total)}</Text>
      <Text x={1360} y={410} size={66} color={MUTED} anchor="middle"
        opacity={arrive(t, 21.4, .2)}>约 174.5 枚</Text>
      <Text x={1360} y={480} size={66} color={MUTED} anchor="middle"
        opacity={arrive(t, 21.4, .2)}>1 枚 = 1,000 元</Text>
    </>}
    {segment === 'S6' && <Text x={960} y={150} size={72} color={GOLD} anchor="middle" weight={600}
      opacity={arrive(t, 25.2, .4)}>让收益，也成为本金。</Text>}
    {segment === 'S7' && <Text x={120} y={170} size={76} weight={600}>复利</Text>}
    <YearLabel t={t}/>
    <Text x={960} y={1046} size={54} color={MUTED} anchor="middle" opacity={footnote}>
      固定10%数学演示，非实际回报 · 不计税费及通胀
    </Text>
  </>;
}

export default function Compound(config: CodeSceneProps) {
  const clock = useSceneContext();
  useEffect(() => {clock.ready();}, []);
  const t = clock.elapsedSeconds;
  const hideText = Boolean((config.props as {hideText?: boolean} | undefined)?.hideText);
  const cam = cameraAt(t);
  const tx = 960 - cam.s * cam.x, ty = 540 - cam.s * cam.y;
  return <div style={{width: config.width, height: config.height, background: BG, overflow: 'hidden'}}>
    <svg viewBox="0 0 1920 1080" width="100%" height="100%" aria-label="复利数学演示">
      <defs>
        <linearGradient id="sweep" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor={OFF_WHITE} stopOpacity="0"/>
          <stop offset=".5" stopColor={OFF_WHITE} stopOpacity=".55"/>
          <stop offset="1" stopColor={OFF_WHITE} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <rect width={1920} height={1080} fill={BG}/>
      <g transform={`translate(${tx} ${ty}) scale(${cam.s})`}>
        {t < 3.5 ? <StartColumns t={t}/> : <>
          <LeftGroup t={t}/>
          <RightColumn t={t}/>
        </>}
        {t >= 19 ? <Hill t={t}/> : null}
      </g>
      {!hideText && <TextLayer t={t}/>}
    </svg>
  </div>;
}
