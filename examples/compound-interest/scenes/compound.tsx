import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {
  FIRST_DISC_INDEX, Disc, Text, BG, DARK_GOLD, GOLD, MUTED, OFF_WHITE,
  columnPositions, endingGridPositions, hillPositions, mixColor, shelfPositions,
  withdrawBlockPositions,
} from './discs';
import {
  clamp, comparison, discDiameter, discFractions, ease, firstGainJourney, money,
  segmentAt, withdrawState, yearAt, yearState,
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
const BLOCK_SOURCE = {x: LEFT_X + 20, y: TOP10 - 40};

const leftColumn = columnPositions(LEFT_X, BASE_Y, 10, PITCH);
const rightColumn = columnPositions(RIGHT_X, BASE_Y, 13, PITCH);
const shelf = shelfPositions(30, 300, 400);
// S5 取出组：10 枚米白本金底排 + 30 枚暗金三排，合起来是可数的 40 枚整块。
const block = withdrawBlockPositions();
const hill = hillPositions(159);
// 与数学精确对应：158.631 枚米白（含 0.631）与 15.863 枚金，不再丢掉零头。
const hillUnits = discFractions(yearState(30).offWhiteUnits);
const finalGold = discFractions(yearState(30).goldUnits);
const goldRow = finalGold.map((unit, i) => ({
  x: HILL_CENTER + (i - (finalGold.length - 1) / 2) * 40,
  y: hill[FIRST_DISC_INDEX].y - 48, unit,
}));
// 结尾回扣：第 1 年赚到的 1,000 元，到第 30 年按 29 个复利期长成 15.863 枚。
const firstGain = firstGainJourney(30);
const firstGainUnits = discFractions(firstGain.atYear / 1000);
const endGrid = endingGridPositions(firstGainUnits.length, 1200, 440);
const firstGainUnitsLabel = (firstGain.atYear / 1000).toFixed(3);
const gap = comparison(30).difference;

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
  // 结尾不再切丘特写：小舞台在中央，镜头只做轻微推进与拉回。
  {t: 27.0, cam: {x: 960, y: 540, s: 1.03}},
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

/** S5 取出组：白柱展开成底排，暗金从柱顶飞入上方三排，形成 40 枚整块。 */
function WithdrawBlock({t}: {t: number}) {
  const pre = ease((t - 19) / .4);
  return <>
    {leftColumn.map((p, i) => {
      const target = block.white[i];
      const p1 = ease(clamp((t - 19.0 - i * .025) / .55));
      const x = p.x + (target.x - p.x) * p1;
      const y = p.y + (target.y - p.y) * p1 - Math.sin(p1 * Math.PI) * 26;
      return <Disc key={`w${i}`} x={x} y={y}/>;
    })}
    {block.dark.map((target, i) => {
      if (i >= 20 && i <= 22) {
        const source = shelf[i - 20];
        return <Disc key={`d${i}`} x={source.x + (target.x - source.x) * pre}
          y={source.y + (target.y - source.y) * pre} state="dark"/>;
      }
      const land = 19.2 + 1.0 * Math.pow(i / 29, .75);
      const p1 = ease(clamp((t - (land - .45)) / .45));
      const x = BLOCK_SOURCE.x + (target.x - BLOCK_SOURCE.x) * p1;
      const y = BLOCK_SOURCE.y + (target.y - BLOCK_SOURCE.y) * p1 - Math.sin(p1 * Math.PI) * 55;
      return <Disc key={`d${i}`} x={x} y={y} state="dark"
        opacity={clamp((t - (land - .45)) / .2)}/>;
    })}
  </>;
}

function LeftGroup({t}: {t: number}) {
  if (t >= 19) return <WithdrawBlock t={t}/>;
  if (t < 13) {
    return <>{leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x} y={p.y}/>)}</>;
  }
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

function Hill({t, hideFirst}: {t: number; hideFirst: boolean}) {
  const spread = ease((t - 19) / .8);
  return <>
    {PRE_TARGETS.map((targetIndex, i) => {
      const target = hill[targetIndex], source = PRE_SOURCES[i];
      const isFirst = targetIndex === FIRST_DISC_INDEX;
      if (isFirst && hideFirst) return null;
      const committing = targetIndex === PRE_TARGETS[12];
      const x = source.x + (target.x - source.x) * spread;
      const y = source.y + (target.y - source.y) * spread;
      return <Disc key={`p${i}`} x={x} y={y} state="white"
        color={committing ? mixColor(GOLD, OFF_WHITE, spread) : undefined}/>;
    })}
    {RAIN_ORDER.map((targetIndex, i) => {
      const p = hill[targetIndex], unit = hillUnits[targetIndex];
      const land = 19.4 + 0.9 * Math.pow(i / Math.max(1, RAIN_ORDER.length - 1), .62);
      const fall = clamp((t - (land - .35)) / .35);
      if (t < land - .35) return null;
      const rim = t > land && t < land + 1 ? GOLD : undefined;
      return <Disc key={`h${targetIndex}`} x={p.x} y={p.y - 340 * (1 - ease(fall))}
        r={discDiameter(unit) / 2} state="white" color={mixColor(GOLD, OFF_WHITE, fall)}
        rim={rim}/>;
    })}
    {goldRow.map((g, i) => {
      const land = 20.0 + i * .02;
      const p = ease(clamp((t - land) / .3));
      if (t < land) return null;
      const start = {x: hill[FIRST_DISC_INDEX].x, y: hill[FIRST_DISC_INDEX].y - 48};
      return <Disc key={`g${i}`} x={start.x + (g.x - start.x) * p}
        y={start.y + (g.y - start.y) * p - Math.sin(p * Math.PI) * 24}
        r={discDiameter(g.unit) / 2} state="gold"/>;
    })}
  </>;
}

/** S6/S7 小舞台：第 1 年收益分成“取走”和“再投入”两种去向。 */
function Ending({t}: {t: number}) {
  const source = hill[FIRST_DISC_INDEX];
  const lift = ease(clamp((t - 24) / .5));
  const glow = ease((t - 24.2) / .3);
  const split = ease(clamp((t - 24.5) / .25));
  const leftX = 680, rightX = 1200, rowY = 440;
  const travelX = source.x + (960 - source.x) * lift;
  const travelY = source.y + (rowY - source.y) * lift - Math.sin(lift * Math.PI) * 70;
  const labels = arrive(t, 24.7, .3);
  const values = arrive(t, 25.4, .3);
  const units = arrive(t, 25.6, .3);
  const conclusion = arrive(t, 26.0, .4);
  const headline = arrive(t, 24.0, .35);
  const title = arrive(t, 27.8, .5);
  return <>
    {t < 24.5 && <Disc x={travelX} y={travelY} color={mixColor(OFF_WHITE, GOLD, glow)}/>}
    {t >= 24.5 && <Disc x={960 + (leftX - 960) * split} y={rowY} state="dark"
      color={mixColor(GOLD, DARK_GOLD, split)}/>}
    {t >= 24.5 && t < 24.7 && <Disc x={960 + (rightX - 960) * split} y={rowY} state="gold"/>}
    {t >= 24.7 && firstGainUnits.map((unit, i) => {
      const start = 24.7 + i * .035;
      if (t < start) return null;
      const p = ease(clamp((t - start) / .5));
      const target = endGrid[i];
      return <Disc key={`e${i}`} x={rightX + (target.x - rightX) * p}
        y={rowY + (target.y - rowY) * p} r={discDiameter(unit) / 2} state="white"
        color={mixColor(GOLD, OFF_WHITE, p)} opacity={clamp((t - start) / .08)}/>;
    })}
    <Text x={960} y={200} size={60} anchor="middle" weight={600}
      opacity={headline}>174,494 元里，第 1 年赚的 1,000 元，到第 30 年</Text>
    <Text x={leftX} y={310} size={60} anchor="middle" opacity={labels}>取走</Text>
    <Text x={rightX} y={310} size={60} color={GOLD} anchor="middle" opacity={labels}>再投入</Text>
    <Text x={leftX} y={650} size={88} anchor="middle" weight={600}
      opacity={values}>{money(1000)}</Text>
    <Text x={rightX} y={650} size={88} color={GOLD} anchor="middle" weight={600}
      opacity={values}>{money(firstGain.atYear)}</Text>
    <Text x={leftX} y={770} size={64} color={MUTED} anchor="middle" opacity={units}>1 枚暗金</Text>
    <Text x={rightX} y={770} size={64} color={MUTED} anchor="middle"
      opacity={units}>{firstGainUnitsLabel} 枚米白</Text>
    <Text x={960} y={880} size={68} color={GOLD} anchor="middle" weight={600}
      opacity={conclusion}>让收益，也成为本金。</Text>
    <Text x={960} y={100} size={72} anchor="middle" weight={600} opacity={title}>复利</Text>
  </>;
}

function YearLabel({t, opacity = 1}: {t: number; opacity?: number}) {
  // S5 的结果标题直接写“第 30 年累计总额”，不再单独报年份，减少结果屏的浮层。
  if (t < 13 || t >= 19) return null;
  return <Text x={1800} y={140} size={62} color={GOLD} anchor="end" weight={600}
    opacity={opacity}>第 {yearAt(t)} 年</Text>;
}

function TextLayer({t}: {t: number}) {
  const segment = segmentAt(t);
  const footnote = arrive(t, 4.4, .5);
  const s5Fade = 1 - arrive(t, 23.8, .2);
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
      <Text x={120} y={125} size={60} color={MUTED} opacity={s5Fade}>{t < 20.2
        ? '同样 10,000 · 同样 10% · 快进到第 30 年'
        : '同样 10,000 · 同样 10% · 第 30 年累计总额（元）'}</Text>
      {t < 20.2 ? <>
        <Text x={500} y={230} size={60} weight={600} anchor="middle" opacity={s5Fade}>收益取走</Text>
        <Text x={1360} y={230} size={60} weight={600} anchor="middle" opacity={s5Fade}>收益再投入</Text>
      </> : <>
        <Text x={500} y={230} size={60} weight={600} anchor="middle"
          opacity={arrive(t, 20.2, .2) * s5Fade}>收益取走 · 40 枚 · 本金 10</Text>
        <Text x={1360} y={230} size={60} weight={600} anchor="middle"
          opacity={arrive(t, 20.2, .2) * s5Fade}>收益再投入 · 约 174.5 枚</Text>
      </>}
      <Text x={500} y={358} size={84} anchor="middle" weight={600}
        opacity={arrive(t, 20.2, .2) * s5Fade}>{money(withdrawState(30).total)}</Text>
      <Text x={1360} y={358} size={88} color={GOLD} anchor="middle" weight={600}
        opacity={arrive(t, 20.2, .2) * s5Fade}>{money(yearState(30).total)}</Text>
      <Text x={970} y={592} size={60} color={GOLD} anchor="middle" weight={600}
        opacity={arrive(t, 20.6, .25) * s5Fade}>相差 {money(gap)} 元</Text>
      <Text x={120} y={700} size={64} color={MUTED}
        opacity={arrive(t, 20.2, .2) * s5Fade}>1 枚 = 1,000 元</Text>
    </>}
    <YearLabel t={t} opacity={segment === 'S5' ? s5Fade : 1}/>
    <Text x={960} y={1046} size={64} color={MUTED} anchor="middle" opacity={footnote}>
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
  // S5 结果退场：先淡文字，再把整组比较淡到 0，结尾小舞台接管画面。
  const bg = t < 24 ? 1 : 1 - ease((t - 24) / .6);
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
        <g opacity={bg}>
          {t < 3.5 ? <StartColumns t={t}/> : <>
            <LeftGroup t={t}/>
            <RightColumn t={t}/>
          </>}
          {t >= 19 ? <Hill t={t} hideFirst={t >= 24}/> : null}
        </g>
        {t >= 24 ? <Ending t={t}/> : null}
        {t >= 27 ? <Sweep t={t}/> : null}
      </g>
      {!hideText && <TextLayer t={t}/>}
    </svg>
  </div>;
}
