import {useEffect, useMemo} from 'react';
import {createSceneEvents, easeMotion, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {
  FIRST_DISC_INDEX, Disc, Text, BG, DARK_GOLD, GOLD, MUTED, OFF_WHITE,
  columnPositions, hillPositions, mixColor, shelfPositions, withdrawBlockPositions,
} from './discs';
import {AXES, hillLandingDelay} from './compoundLayout';
import {clamp, discDiameter, discFractions, segmentAt, yearState} from './compoundMath';

const LEFT_X = AXES.left;
const RIGHT_X = AXES.right;
const HILL_CENTER = AXES.hill;
const BASE_Y = 900;
const PITCH = 28;
const TOP10 = BASE_Y - 9 * PITCH;        // 648
const FIRST_GOLD_Y = 590;
const GOLD_REST = 586;
const NEW_GOLD_Y = 558;
const BLOCK_SOURCE = {x: LEFT_X + 20, y: TOP10 - 40};

/** 四级字阶：112 片名/主题卡、88 结论与结果数字、80 年份与主张、60 对象名与口径。 */
const TYPE = {title: 112, hero: 88, heading: 80, body: 60} as const;

const leftColumn = columnPositions(LEFT_X, BASE_Y, 10, PITCH);
const rightColumn = columnPositions(RIGHT_X, BASE_Y, 13, PITCH);
const shelf = shelfPositions(30, 200, 470);
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

// S4 结束时的 12 枚米白 + 第 3 年已转为资本的那枚。第 11 枚（下标 10）是第一年的收益，
// 在丘上固定映射到顶行中央，作为金色顶排的生长起点。
const PRE_TARGETS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, FIRST_DISC_INDEX, 10, 11];
const PRE_SOURCES = [...rightColumn.slice(0, 12), {x: RIGHT_X, y: NEW_GOLD_Y}];
const RAIN_TARGETS = hill.map((_, i) => i).filter(i => !PRE_TARGETS.includes(i));
// 金雨按丘的行列顺序落定：先下后上、同排从左到右，让“多出来多少”可被数出来。
const RAIN_ORDER = [...RAIN_TARGETS].sort((a, b) => a - b);

type Cam = {x: number; y: number; s: number};
const CAM_KEYS: {t: number; cam: Cam}[] = [
  // 主题卡退场时两柱已推近，主体不再只是画面里的一条窄柱。
  {t: 0, cam: {x: 960, y: 660, s: 1.6}},
  {t: 3.65, cam: {x: 960, y: 660, s: 1.6}},
  // S2 金币出现时给一次微距，再回到能完整看到柱顶的取景。
  {t: 4.35, cam: {x: RIGHT_X, y: 620, s: 3.0}},
  {t: 4.75, cam: {x: RIGHT_X, y: 600, s: 4.2}},
  {t: 5.45, cam: {x: RIGHT_X, y: 600, s: 4.2}},
  {t: 6.25, cam: {x: RIGHT_X, y: 758, s: 2.4}},
  {t: 8.0, cam: {x: RIGHT_X, y: 758, s: 2.4}},
  {t: 12.2, cam: {x: RIGHT_X, y: 758, s: 2.4}},
  {t: 13.4, cam: {x: 960, y: 540, s: 1.02}},
  {t: 18.8, cam: {x: 960, y: 540, s: 1.02}},
  // 结果屏略缩小，给左下角口径与丘底之间留出呼吸；缓慢漂移避免判定冻结。
  {t: 19.6, cam: {x: 960, y: 540, s: .89}},
  {t: 24.8, cam: {x: 960, y: 540, s: .88}},
];

// S6 单独一幕：24.8 秒硬切到丘顶特写，归队后拉回全景，只剩白色本金堆。
const CLOSING_KEYS: {t: number; cam: Cam}[] = [
  {t: 24.8, cam: {x: HILL_CENTER, y: 660, s: 2.0}},
  {t: 26.2, cam: {x: HILL_CENTER, y: 660, s: 2.08}},
  {t: 26.9, cam: {x: HILL_CENTER, y: 540, s: .95}},
  {t: 29, cam: {x: HILL_CENTER, y: 540, s: .93}},
];

/** 把世界 x 投影到屏幕 x；文字是屏幕层的，必须跟着对应镜头缩放。 */
const projectX = (x: number, cam: Cam) => 960 - cam.s * (cam.x - x);
const projectY = (y: number, cam: Cam) => 540 - cam.s * (cam.y - y);
const S1_LABEL_X = {left: projectX(LEFT_X, CAM_KEYS[0].cam), right: projectX(RIGHT_X, CAM_KEYS[0].cam)};
// 标签贴近柱顶，避免与左上角的标题、问题挤成同一块文字。
const S1_LABEL_Y = projectY(604, CAM_KEYS[0].cam);
const S4_CAM = {x: 960, y: 540, s: 1.02};
const S5_CAM = {x: 960, y: 540, s: .885};

// 命名缓动：入场减速、离场加速、画面内两端平滑、相机 easeInOutSine、落定回弹。
const easeOut = (p: number) => easeMotion('easeOutCubic', p);
const easeOutQuint = (p: number) => easeMotion('easeOutQuint', p);
const easeIn = (p: number) => easeMotion('easeInCubic', p);
const easeInOut = (p: number) => easeMotion('easeInOutCubic', p);
const easeSine = (p: number) => easeMotion('easeInOutSine', p);
const settleCurve = (p: number) => easeMotion('backOut', p);

function between(t: number, keys: {t: number; cam: Cam}[]): Cam {
  let index = 0;
  while (index < keys.length - 2 && t > keys[index + 1].t) index++;
  const from = keys[index], to = keys[index + 1];
  const p = easeSine((t - from.t) / Math.max(1e-6, to.t - from.t));
  return {x: from.cam.x + (to.cam.x - from.cam.x) * p,
    y: from.cam.y + (to.cam.y - from.cam.y) * p,
    s: Math.exp(Math.log(from.cam.s) + (Math.log(to.cam.s) - Math.log(from.cam.s)) * p)};
}

function cameraAt(t: number): Cam {
  return between(t, t >= 24.8 ? CLOSING_KEYS : CAM_KEYS);
}

const arrive = (t: number, at: number, duration = .5) => easeOut((t - at) / duration);
function StartColumns({t, events, fps}: {t: number; events: ReturnType<typeof createSceneEvents>; fps: number}) {
  return <>
    {[LEFT_X, RIGHT_X].map(x => columnPositions(x, BASE_Y, 10, PITCH).map((p, i) => {
      const land = events.frame(`drop-${i + 1}`) / fps;
      if (t < land - .45) return null;
      const p1 = easeIn(clamp((t - (land - .45)) / .45));
      // 落定一沉：接触后一次小回弹，全片签名动作之一。
      const bounce = t > land ? Math.sin((t - land) * 17) * 5 * Math.exp(-(t - land) * 9) : 0;
      return <Disc key={`${x}-${i}`} x={p.x} y={-60 + (p.y + 60) * p1 + bounce}
        opacity={clamp((t - (land - .45)) / .18)}/>;
    }))}
  </>;
}

function RightColumn({t}: {t: number}) {
  if (t < 8) {
    const grow = easeOutQuint(clamp((t - 4.2) / .9));
    const float = easeSine(clamp((t - 5.2) / 1.4));
    const settle = settleCurve(clamp((t - 6.6) / .8));
    const gy = 618 - 40 * float + 12 * settle;
    return <>
      {rightColumn.slice(0, 10).map((p, i) => <Disc key={`r${i}`} x={p.x} y={p.y}/>)}
      {grow > 0 && <g transform={`rotate(${30 * float} ${RIGHT_X} ${gy})`}>
        <Disc x={RIGHT_X} y={gy} r={21 * grow} state="gold"/>
      </g>}
    </>;
  }
  if (t < 13) {
    // 回吸前 0.08 秒预备：先停一拍，再下落变米白。
    const ret = easeInOut(clamp((t - 8.08) / 1.0));
    const pulse = t > 9.4 && t < 10.6 ? Math.sin((t - 9.4) * Math.PI / .6) : 0;
    const grow = easeOutQuint(clamp((t - 10.2) / .9));
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
    const commit = easeInOut(clamp((t - 15.2) / 1.0));
    const merge = easeInOut(clamp((t - 15.2) / .8));
    const grow = easeOutQuint(clamp((t - 16.0) / .9));
    const shelfIn = easeOut(clamp((t - 12.6) / .6));
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
  const pre = easeOut(clamp((t - 19) / .4));
  return <>
    {leftColumn.map((p, i) => {
      const target = block.white[i];
      const p1 = easeOut(clamp((t - 19.0 - i * .025) / .55));
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
      const p1 = easeOut(clamp((t - (land - .45)) / .45));
      const x = BLOCK_SOURCE.x + (target.x - BLOCK_SOURCE.x) * p1;
      const y = BLOCK_SOURCE.y + (target.y - BLOCK_SOURCE.y) * p1 - Math.sin(p1 * Math.PI) * 55;
      return <Disc key={`d${i}`} x={x} y={y} state="dark"
        opacity={clamp((t - (land - .45)) / .2)}/>;
    })}
  </>;
}

function LeftGroup({t}: {t: number}) {
  // S2–S3 的相机聚焦右柱，左柱完全在画面外；不渲染不可见对象，也避免裁切误判。
  if (t >= 4.5 && t < 12.7) return null;
  if (t >= 19) return <WithdrawBlock t={t}/>;
  if (t < 13) {
    return <>{leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x} y={p.y}/>)}</>;
  }
  const appear = easeOut(clamp((t - 13.6) / .5));
  const fly = easeInOut(clamp((t - 14.2) / 1.0));
  const target = shelf[2];
  const x = LEFT_X + (target.x - LEFT_X) * fly;
  const y = (TOP10 - 40) + (target.y - (TOP10 - 40)) * fly - Math.sin(fly * Math.PI) * 90;
  return <>
    {leftColumn.map((p, i) => <Disc key={`l${i}`} x={p.x} y={p.y}/>)}
    {appear > 0 && shelf.slice(0, 2).map((p, i) => <Disc key={`pre${i}`} x={p.x} y={p.y} state="dark"/>) }
    {appear > 0 && <Disc x={x} y={y} state="gold" opacity={appear}
      color={mixColor(GOLD, DARK_GOLD, fly)} rim={t < 15.2 ? GOLD : undefined}/>}
  </>;
}

function Hill({t}: {t: number}) {
  const spread = easeOut(clamp((t - 19) / .8));
  return <>
    {PRE_TARGETS.map((targetIndex, i) => {
      const target = hill[targetIndex], source = PRE_SOURCES[i];
      const committing = targetIndex === PRE_TARGETS[12];
      const x = source.x + (target.x - source.x) * spread;
      const y = source.y + (target.y - source.y) * spread;
      return <Disc key={`p${i}`} x={x} y={y} state="white"
        color={committing ? mixColor(GOLD, OFF_WHITE, spread) : undefined}/>;
    })}
    {RAIN_ORDER.map(targetIndex => {
      const p = hill[targetIndex], unit = hillUnits[targetIndex];
      const land = 19.4 + hillLandingDelay(targetIndex);
      const fall = easeIn(clamp((t - (land - .35)) / .35));
      if (t < land - .35) return null;
      const rim = t > land && t < land + 1 ? GOLD : undefined;
      return <Disc key={`h${targetIndex}`} x={p.x} y={p.y - 340 * (1 - fall)}
        r={discDiameter(unit) / 2} state="white" color={mixColor(GOLD, OFF_WHITE, fall)}
        rim={rim}/>;
    })}
    {goldRow.map((g, i) => {
      const land = 20.6 + i * .02;
      const p = easeOut(clamp((t - land) / .3));
      if (t < land) return null;
      const start = {x: hill[FIRST_DISC_INDEX].x, y: hill[FIRST_DISC_INDEX].y - 48};
      // S6：16 枚金片逐枚下沉到白堆顶；变白只在下沉末端 0.12 秒内完成，避免整条色带糊开。
      const sinkStart = 24.95 + i * .055;
      const sink = easeInOut(clamp((t - sinkStart) / .5));
      const colorMix = clamp((t - (sinkStart + .30)) / .12);
      return <Disc key={`g${i}`} x={start.x + (g.x - start.x) * p}
        y={start.y + (g.y - start.y) * p - Math.sin(p * Math.PI) * 24 + 26 * sink}
        r={discDiameter(g.unit) / 2} state={colorMix >= 1 ? 'white' : 'gold'}
        color={colorMix > 0 ? mixColor(GOLD, OFF_WHITE, colorMix) : undefined}/>;
    })}
  </>;
}

function TextLayer({t}: {t: number}) {
  const segment = segmentAt(t);
  // S6 丘顶特写时口径会压在圆片上，24.6–24.8 淡出，拉回全景后 26.9 起恢复。
  // S2 金币微距期间柱体占满下半画面，口径同样让位，离开微距后立即恢复。
  const footnote = arrive(t, 4.4, .5) * (1 - arrive(t, 24.6, .2) + arrive(t, 26.9, .3))
    * (1 - arrive(t, 4.25, .2) + arrive(t, 6.15, .3));
  // 开场标签在 S2 推近的头 0.35 秒内淡出，避免镜头移动时标签与柱脱开。
  // 主题卡 1.04 秒退净；两柱 1.0 秒起落，标题随之进入，避免与主题卡同屏。
  const approach = arrive(t, 1.8, .3) * (1 - arrive(t, 3.5, .15));
  return <>
    {segment === 'S1' && <>
      <rect width={1920} height={1080} fill={BG} opacity={1 - arrive(t, .82, .22)}/>
      <Text x={960} y={560} size={TYPE.title} anchor="middle" weight={600}
        opacity={1 - arrive(t, .72, .14)}>复利的力量</Text>
    </>}
    {approach > 0 && <>
      <Text x={S1_LABEL_X.left} y={S1_LABEL_Y} size={TYPE.body} anchor="middle"
        opacity={approach}>收益取走</Text>
      <Text x={S1_LABEL_X.right} y={S1_LABEL_Y} size={TYPE.body} anchor="middle"
        opacity={approach}>收益再投入</Text>
    </>}
    {segment === 'S1' && <>
      <Text x={120} y={170} size={TYPE.heading} weight={600}
        opacity={arrive(t, 1.0, .3)}>同样一万，两种做法</Text>
      <Text x={120} y={290} size={TYPE.body} color={MUTED}
        opacity={arrive(t, 2.2, .4)}>三十年后差多少？</Text>
    </>}
    {segment === 'S2' && <>
      <Text x={120} y={150} size={TYPE.heading} weight={600}>第 1 年</Text>
      <Text x={120} y={280} size={TYPE.body} color={MUTED}
        opacity={1 - arrive(t, 6.6, .3)}>10,000 × 10% = 1,000</Text>
    </>}
    {segment === 'S3' && <>
      <Text x={120} y={150} size={TYPE.heading} weight={600}>第 2 年</Text>
    </>}
    {segment === 'S4' && <>
      <Text x={projectX(LEFT_X, S4_CAM)} y={300} size={TYPE.body} weight={600} anchor="middle">收益取走</Text>
      <Text x={projectX(LEFT_X, S4_CAM)} y={390} size={TYPE.body} color={MUTED} anchor="middle">拿走，不再生息</Text>
      <Text x={projectX(RIGHT_X, S4_CAM)} y={300} size={TYPE.body} weight={600} anchor="middle">收益再投入</Text>
      <Text x={projectX(RIGHT_X, S4_CAM)} y={390} size={TYPE.body} color={MUTED} anchor="middle">留在里面，继续生息</Text>
    </>}
    {segment === 'S5' && <>
      <Text x={120} y={125} size={TYPE.body} color={MUTED}>{t < 21.0
        ? '同样 10,000，同样 10%，快进到第 30 年'
        : '30 年后的总资产'}</Text>
      <Text x={projectX(300 + 4.5 * 42, S5_CAM)} y={260} size={TYPE.body} weight={600} anchor="middle">收益取走</Text>
      <Text x={projectX(HILL_CENTER, S5_CAM)} y={260} size={TYPE.body} weight={600} anchor="middle">收益再投入</Text>
      <Text x={projectX(300 + 4.5 * 42, S5_CAM)} y={385} size={TYPE.hero} anchor="middle" weight={600}
        opacity={arrive(t, 21.0, .2)}>40 枚</Text>
      <Text x={projectX(HILL_CENTER, S5_CAM)} y={385} size={TYPE.hero} anchor="middle" weight={600}
        opacity={arrive(t, 21.0, .2)}>约 174.5 枚</Text>
    </>}
    {segment === 'S6' && <>
      {t >= 26.9 && <Text x={960} y={610} size={TYPE.hero} anchor="middle" weight={600}
        opacity={arrive(t, 26.9, .4)}>让收益，也成为本金。</Text>}
      {t >= 27.1 && <Text x={960} y={150} size={TYPE.title} anchor="middle" weight={600}
        opacity={arrive(t, 27.1, .35)}>复利</Text>}
    </>}
    <Text x={120} y={1044} size={TYPE.body} color={MUTED} opacity={footnote}>
      固定10%数学演示，非实际回报 · 不计税费及通胀
    </Text>
  </>;
}

export default function Compound(config: CodeSceneProps) {
  const clock = useSceneContext();
  const events = useMemo(() => createSceneEvents(config.eventFrames), [config.eventFrames]);
  useEffect(() => {clock.ready();}, []);
  const t = clock.elapsedSeconds;
  const hideText = Boolean((config.props as {hideText?: boolean} | undefined)?.hideText);
  const cam = cameraAt(t);
  const tx = 960 - cam.s * cam.x, ty = 540 - cam.s * cam.y;
  return <div style={{width: config.width, height: config.height, background: BG, overflow: 'hidden'}}>
    <svg viewBox="0 0 1920 1080" width="100%" height="100%" aria-label="复利数学演示">
      <rect width={1920} height={1080} fill={BG}/>
      <g transform={`translate(${tx} ${ty}) scale(${cam.s})`}>
        {t < 3.5 ? <StartColumns t={t} events={events} fps={config.fps}/> : t < 24.8 ? <>
          <LeftGroup t={t}/>
          <RightColumn t={t}/>
        </> : null}
        {t >= 19 ? <Hill t={t}/> : null}
      </g>
      {!hideText && <TextLayer t={t}/>}
    </svg>
  </div>;
}
