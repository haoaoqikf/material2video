/**
 * 《样本》规范示例：你看到的是样本，还是总体？
 *
 * 全片只问一件事。3 个金点、1000 个点、点阵上的线、均值回归与盲人摸象，
 * 都是同一母题的不同尺度。八拍时间表、数学口径与唯一硬切见 DESIGN.md。
 *
 * 画面全部由本文件的几何与 `dark-proof` 组件构造；不使用参考片的画面、字幕、
 * 文案或音轨。所有变化由帧号驱动，随机点使用固定种子。
 */
import {useEffect, useRef} from 'react';
import {hashSeed, seededRandom, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import Stage from 'm2v/style/components/stage';
import HeroNumber from 'm2v/style/components/hero-number';
import Counter from 'm2v/style/components/counter';
import DotField, {type DotPoint} from 'm2v/style/components/dot-field';
import {ChartArrow, ChartFrame, ChartLine, ChartMarker} from 'm2v/style/components/proof-chart';
import BilingualTitle from 'm2v/style/components/bilingual-title';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
import HandDrawnLine from 'm2v/style/components/hand-drawn-line';
import {
  LATIN, NUMERIC_STYLE, SANS, T, easeInOutSine, easeOutCubic,
  frameProgress, lerp, mixColor,
} from 'm2v/style/components/kit';

type Subtitle = {startFrame: number; endFrame: number; text: string};
type Props = {screenSubtitles?: Subtitle[]};

const IVORY = T.colors.ivory;
const GOLD = T.colors.gold;
const EMBER = T.colors.ember;
const MUTED = T.colors.muted;
const LINE = T.colors.line;

const FIELD_BOX = {x: 620, y: 250, width: 1060, height: 540};
const RETURN_BOX = {x: 640, y: 270, width: 1040, height: 540};

const W = 1920;
const H = 1080;

function gaussian(random: () => number): number {
  let sum = 0;
  for (let index = 0; index < 12; index += 1) sum += random();
  return sum - 6;
}

/** 1000 个点：50 列 × 20 行，固定抖动；3 个金点是同一字段里的相邻点。 */
const FIELD_POINTS: DotPoint[] = (() => {
  const random = seededRandom(hashSeed('dark-proof/sample/field'));
  const points: DotPoint[] = [];
  for (let row = 0; row < 20; row += 1) {
    for (let col = 0; col < 50; col += 1) {
      points.push({
        x: (col + 0.5 + (random() - 0.5) * 0.58) / 50,
        y: (row + 0.5 + (random() - 0.5) * 0.58) / 20,
        tone: 'muted',
      });
    }
  }
  return points;
})();

//: 1000 点阵中 3 个金点的下标：50 列 × 20 行，524/525/526 是第 10 行相邻三点。
const GOLD_INDEX = [524, 525, 526];
const GOLD_POINTS = GOLD_INDEX.map(index => ({
  x: FIELD_POINTS[index].x,
  y: FIELD_POINTS[index].y,
  radius: 13,
  halo: true,
  tone: 'gold' as const,
}));

const COLUMN_SPEC = [
  {n: 3, cx: 430, half: 74, se: 14.43},
  {n: 10, cx: 770, half: 82, se: 7.91},
  {n: 100, cx: 1110, half: 100, se: 2.5},
  {n: 1000, cx: 1450, half: 120, se: 0.79},
];

const COLUMN_POINTS = COLUMN_SPEC.map(spec => {
  const random = seededRandom(hashSeed(`dark-proof/sample/column-${spec.n}`));
  const points: DotPoint[] = [];
  for (let index = 0; index < spec.n; index += 1) {
    const x = spec.cx + (random() - 0.5) * spec.half * 2;
    const y = 550 - gaussian(random) * 25 * 7;
    points.push({x: x / W, y: Math.min(820, Math.max(260, y)) / H, tone: 'muted'});
  }
  return {spec, points};
});

/** 大象轮廓与耳朵：原创路径，只表达“一个整体被分成局部观察”。 */
const ELEPHANT = `M170 300 C128 330 108 382 98 432 C84 502 68 572 94 616
  C110 640 141 632 151 602 C166 558 166 505 180 468 C208 482 232 508 240 548
  L270 598 C282 616 308 616 320 596 L338 558 C392 572 470 574 520 564
  L566 604 C580 620 606 618 618 598 L642 554 C700 550 752 514 770 458
  C796 452 814 426 808 398 C832 382 838 350 820 328 C842 308 836 274 810 262
  C782 230 730 220 684 238 C642 208 582 198 534 216 C490 192 432 194 394 222
  C342 212 290 232 268 270 C226 268 192 282 170 300 Z`;
const EAR = `M360 238 C412 240 438 300 426 362 C416 418 370 446 334 424
  C306 396 300 320 360 238 Z`;

const EX = (x: number) => 520 + x * 0.82;
const EY = (y: number) => 170 + y * 0.82;

function log10(value: number): number {
  return Math.log(value) / Math.LN10;
}

function fadeIn(frame: number, start: number, end: number): number {
  return easeOutCubic(frameProgress(frame, start, end - start));
}

function fadeOut(frame: number, start: number, end: number): number {
  return 1 - easeInOutSine(frameProgress(frame, start, end - start));
}

function windowOpacity(frame: number, inStart: number, inEnd: number, outStart: number, outEnd: number): number {
  return fadeIn(frame, inStart, inEnd) * fadeOut(frame, outStart, outEnd);
}

/** 三段评价的均值：100 → 67 → 33 → 67，每次翻转一条。 */
const SWINGS = [
  {at: 235, values: [100, 100, 0]},
  {at: 285, values: [100, 0, 0]},
  {at: 335, values: [100, 0, 100]},
];

function reviewValues(frame: number): number[] {
  let values = [100, 100, 100];
  for (const swing of SWINGS) {
    const progress = easeInOutSine(frameProgress(frame, swing.at, 18));
    values = values.map((value, index) => lerp(value, swing.values[index], progress));
  }
  return values;
}

/** 均值计数只按最近一次翻转求值；进度保持原始 0–1，由 Counter 自己缓动。 */
function meanCounter(frame: number): {from: number; to: number; progress: number} {
  let from = 100;
  let to = 100;
  let progress = 1;
  for (const swing of SWINGS) {
    const target = swing.values.reduce((sum, value) => sum + value, 0) / swing.values.length;
    if (frame < swing.at) break;
    from = to;
    to = target;
    progress = frameProgress(frame, swing.at, 18);
  }
  return {from, to, progress};
}

function ReviewDisc({x, y, value, opacity}: {x: number; y: number; value: number; opacity: number}) {
  const tone = value >= 50 ? IVORY : EMBER;
  return (
    <div style={{
      position: 'absolute', left: x, top: y, transform: 'translate(-50%, -50%)',
      width: 124, height: 124, borderRadius: '50%', border: `2px solid ${tone}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(10, 11, 13, 0.86)', opacity,
    }}>
      <span style={{...NUMERIC_STYLE, fontSize: 44, lineHeight: 1, color: tone}}>
        {Math.round(value)}
      </span>
    </div>
  );
}

function Opening({frame, opacity}: {frame: number; opacity: number}) {
  const enter = 0.08 + 0.92 * easeOutCubic(frameProgress(frame, 0, 34));
  const move = easeInOutSine(frameProgress(frame, 62, 70));
  const fieldIn = fadeIn(frame, 78, 138);
  const fieldReveal = easeInOutSine(frameProgress(frame, 88, 76));
  const goldIn = easeOutCubic(frameProgress(frame, 92, 44));
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <HeroNumber
        value="3"
        x={lerp(960, 360, move)}
        y={lerp(520, 500, move)}
        size={lerp(300, 240, move)}
        color={GOLD}
        opacity={enter}
        scale={lerp(1.14, 1, enter)}
      />
      <div style={{
        position: 'absolute', left: lerp(960, 360, move), top: lerp(682, 668, move),
        transform: 'translate(-50%, -50%)', fontFamily: SANS, fontSize: 60,
        color: IVORY, opacity: fadeIn(frame, 34, 72), whiteSpace: 'nowrap',
      }}>条评价</div>
      <DotField
        box={FIELD_BOX}
        points={FIELD_POINTS}
        opacity={fieldIn * 0.62}
        reveal={fieldReveal}
        emphasis={GOLD_POINTS}
        emphasisOpacity={goldIn}
      />
      <div style={{
        position: 'absolute', left: FIELD_BOX.x + 20, top: FIELD_BOX.y + FIELD_BOX.height + 22,
        fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: 34, color: GOLD,
        opacity: fadeIn(frame, 128, 160), letterSpacing: '0.04em',
      }}>3 / 1000 = 0.3%</div>
      <div style={{
        position: 'absolute', left: FIELD_BOX.x + 20, top: FIELD_BOX.y - 54,
        fontFamily: LATIN, fontSize: 22, letterSpacing: '0.18em', color: MUTED,
        opacity: fadeIn(frame, 96, 132), textTransform: 'uppercase',
      }}>the whole field</div>
    </div>
  );
}

function Swings({frame, opacity}: {frame: number; opacity: number}) {
  const values = reviewValues(frame);
  const counter = meanCounter(frame);
  const swingIn = fadeIn(frame, 226, 262);
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <DotField box={FIELD_BOX} points={FIELD_POINTS} opacity={0.06} reveal={1}/>
      <div style={{
        position: 'absolute', left: 960, top: 196, transform: 'translate(-50%, -50%)',
        fontFamily: SANS, fontSize: 44, color: MUTED, opacity: fadeIn(frame, 168, 204),
      }}>3 条评价的均值</div>
      <Counter
        from={counter.from}
        to={counter.to}
        progress={counter.progress}
        x={960}
        y={372}
        size={270}
        color={GOLD}
        opacity={fadeIn(frame, 166, 202)}
      />
      <div style={{
        position: 'absolute', left: 960, top: 520, transform: 'translate(-50%, -50%)',
        fontFamily: LATIN, fontSize: 22, letterSpacing: '0.2em', color: MUTED,
        opacity: fadeIn(frame, 174, 210), textTransform: 'uppercase',
      }}>mean of three</div>
      {values.map((value, index) => (
        <ReviewDisc key={index} x={720 + index * 240} y={690} value={value}
          opacity={fadeIn(frame, 170, 206)}/>
      ))}
      <div style={{
        position: 'absolute', left: 960, top: 804, transform: 'translate(-50%, -50%)',
        fontFamily: SANS, fontSize: 34, color: IVORY, opacity: swingIn, whiteSpace: 'nowrap',
      }}>一条评价 = 33 点摆动</div>
      <div style={{
        position: 'absolute', left: 960, top: 852, transform: 'translate(-50%, -50%)',
        fontFamily: LATIN, fontSize: 22, letterSpacing: '0.16em', color: MUTED,
        opacity: fadeIn(frame, 244, 280), textTransform: 'uppercase',
      }}>one review, thirty three points</div>
    </div>
  );
}

function SampleSize({frame, opacity}: {frame: number; opacity: number}) {
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <div style={{
        position: 'absolute', left: 96, top: 140,
        fontFamily: SANS, fontSize: 30, color: GOLD, opacity: fadeIn(frame, 396, 432),
      }}>误差 ∝ 1/√n</div>
      <div style={{
        position: 'absolute', left: 96, top: 176,
        fontFamily: LATIN, fontSize: 21, letterSpacing: '0.16em', color: MUTED,
        opacity: fadeIn(frame, 406, 442), textTransform: 'uppercase',
      }}>σ = 25 · same distribution</div>
      {COLUMN_POINTS.map(({spec, points}, index) => {
        const reveal = easeInOutSine(frameProgress(frame, 376 + index * 38, 52));
        const show = fadeIn(frame, 376 + index * 38, 416 + index * 38);
        const top = 550 - spec.se * 7;
        const bottom = 550 + spec.se * 7;
        return (
          <div key={spec.n} style={{position: 'absolute', inset: 0}}>
            <DotField box={{x: 0, y: 0, width: W, height: H}} points={points}
              opacity={0.58 * show} reveal={reveal} radius={3.2}/>
            <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
              style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
              <g opacity={show}>
                <line x1={spec.cx} y1={top} x2={spec.cx} y2={bottom} stroke={GOLD} strokeWidth={5}
                  strokeLinecap="round"/>
                <line x1={spec.cx - 22} y1={top} x2={spec.cx + 22} y2={top} stroke={GOLD} strokeWidth={5}
                  strokeLinecap="round"/>
                <line x1={spec.cx - 22} y1={bottom} x2={spec.cx + 22} y2={bottom} stroke={GOLD} strokeWidth={5}
                  strokeLinecap="round"/>
                <circle cx={spec.cx} cy={550} r={8} fill={GOLD}/>
              </g>
            </svg>
            <div style={{
              position: 'absolute', left: spec.cx, top: 212, transform: 'translate(-50%, -50%)',
              fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: 34, color: IVORY,
              opacity: show, whiteSpace: 'nowrap',
            }}>{`n = ${spec.n}`}</div>
            <div style={{
              position: 'absolute', left: spec.cx, top: 248, transform: 'translate(-50%, -50%)',
              fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: 22, color: MUTED,
              opacity: show, whiteSpace: 'nowrap',
            }}>{`±${spec.se.toFixed(1)}`}</div>
          </div>
        );
      })}
      <div style={{
        position: 'absolute', left: 960, top: 846, transform: 'translate(-50%, -50%)',
        fontFamily: SANS, fontSize: 30, color: IVORY, opacity: fadeIn(frame, 540, 576),
      }}>同样的分布，不同的样本量</div>
    </div>
  );
}

const THREE_POINTS: Array<[number, number]> = [[620, 680], [960, 540], [1300, 420]];
const TREND = `M620 680 C780 640 820 600 960 540 C1100 480 1160 450 1300 420`;

function ThreeDots({frame, opacity}: {frame: number; opacity: number}) {
  const again = 1;
  const line = easeInOutSine(frameProgress(frame, 626, 74));
  const field = fadeIn(frame, 700, 756);
  const dissolve = easeInOutSine(frameProgress(frame, 738, 64));
  const lineColor = mixColor(IVORY, EMBER, dissolve);
  const lineOpacity = 1 - dissolve;
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <DotField box={{x: 470, y: 250, width: 980, height: 540}} points={FIELD_POINTS}
        opacity={field * 0.34} reveal={1} radius={3}/>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <HandDrawnLine d={TREND} color={lineColor} width={9} progress={line} opacity={lineOpacity}/>
        {THREE_POINTS.map(([x, y], index) => (
          <g key={index} opacity={again}>
            <circle cx={x} cy={y} r={20} fill="none" stroke={GOLD} strokeWidth={1.5} opacity={0.32}/>
            <circle cx={x} cy={y} r={11} fill={GOLD}/>
          </g>
        ))}
      </svg>
    </div>
  );
}

function Regression({frame, opacity}: {frame: number; opacity: number}) {
  const first = fadeIn(frame, 818, 854);
  const second = fadeIn(frame, 888, 924);
  const arrows = easeInOutSine(frameProgress(frame, 926, 90));
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <BilingualTitle zh="均值回归" en="regression to the mean" x={96} y={168} size={60}
        opacity={fadeIn(frame, 820, 856)} ruleWidth={64}/>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <ChartLine points={[[340, 530], [1600, 530]]} color={LINE} width={2} dashed/>
        <text x={1624} y={537} fontFamily={SANS} fontSize={22} fill={MUTED}>总体均值</text>
        <ChartArrow from={[660, 360]} to={[1040, 464]} bend={-64} color={MUTED} width={4}
          progress={arrows} opacity={0.8}/>
        <ChartArrow from={[660, 608]} to={[1040, 550]} bend={64} color={MUTED} width={4}
          progress={arrows} opacity={0.8}/>
        <ChartMarker x={560} y={337} radius={13} color={MUTED} opacity={first}
          label="第一次 92" labelColor={MUTED} labelY={300}/>
        <ChartMarker x={1120} y={475} radius={13} color={GOLD} halo opacity={second}
          label="第二次 62" labelColor={GOLD} labelY={438}/>
        <ChartMarker x={560} y={631} radius={13} color={MUTED} opacity={first}
          label="第一次 28" labelColor={MUTED} labelY={682}/>
        <ChartMarker x={1120} y={539} radius={13} color={GOLD} halo opacity={second}
          label="第二次 48" labelColor={GOLD} labelY={586}/>
      </svg>
    </div>
  );
}

function Elephant({frame, opacity}: {frame: number; opacity: number}) {
  const outline = easeInOutSine(frameProgress(frame, 1028, 100));
  const windows = windowOpacity(frame, 1138, 1176, 1200, 1246);
  const whole = fadeIn(frame, 1194, 1252);
  const windowsSpec = [
    {label: '局部一', x: EX(120), y: EY(540)},
    {label: '局部二', x: EX(370), y: EY(335)},
    {label: '局部三', x: EX(600), y: EY(585)},
  ];
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <BilingualTitle zh="盲人摸象" en="the blind men and the elephant" x={180} y={196} size={60}
        opacity={fadeIn(frame, 1028, 1064)} ruleWidth={64}/>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <defs>
          <clipPath id="sample-elephant-clip"><path d={ELEPHANT} transform="translate(520 170) scale(0.82)"/></clipPath>
          {windowsSpec.map((window, index) => (
            <clipPath id={`sample-window-${index}`} key={index}>
              <circle cx={window.x} cy={window.y} r={72}/>
            </clipPath>
          ))}
        </defs>
        <path d={ELEPHANT} transform="translate(520 170) scale(0.82)" fill={IVORY} opacity={0.045 * whole}/>
        <path d={ELEPHANT} transform="translate(520 170) scale(0.82)" fill="none" stroke={IVORY}
          strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" opacity={0.18 * outline}/>
        <g transform="translate(520 170) scale(0.82)">
          <HandDrawnLine d={ELEPHANT} color={IVORY} width={11} progress={outline}/>
          <HandDrawnLine d={EAR} color={IVORY} width={9} progress={outline} ghostOffset={0.8}/>
        </g>
        <g clipPath="url(#sample-elephant-clip)" opacity={whole}>
          <path d="M760 420 C850 380 930 420 990 500" fill="none" stroke={IVORY} strokeWidth={3} opacity={0.2}/>
          <path d="M780 470 C860 430 940 470 1000 550" fill="none" stroke={IVORY} strokeWidth={3} opacity={0.16}/>
        </g>
        {windowsSpec.map((window, index) => (
          <g key={index} opacity={windows}>
            <circle cx={window.x} cy={window.y} r={72} fill="none" stroke={GOLD} strokeWidth={2} opacity={0.85}/>
            <g clipPath={`url(#sample-window-${index})`}>
              {index === 0 ? (
                <g stroke={IVORY} strokeWidth={3} fill="none" opacity={0.62}>
                  <path d={`M${window.x - 30} ${window.y - 70} C${window.x - 40} ${window.y - 20} ${window.x - 20} ${window.y + 20} ${window.x - 30} ${window.y + 70}`}/>
                  <path d={`M${window.x} ${window.y - 72} C${window.x - 10} ${window.y - 20} ${window.x + 10} ${window.y + 20} ${window.x} ${window.y + 72}`}/>
                  <path d={`M${window.x + 30} ${window.y - 70} C${window.x + 20} ${window.y - 20} ${window.x + 40} ${window.y + 20} ${window.x + 30} ${window.y + 70}`}/>
                </g>
              ) : index === 1 ? (
                <g stroke={IVORY} strokeWidth={3} fill="none" opacity={0.55}>
                  {[20, 40, 60].map(radius => (
                    <circle key={radius} cx={window.x} cy={window.y} r={radius}/>
                  ))}
                </g>
              ) : (
                <g stroke={IVORY} strokeWidth={3} fill="none" opacity={0.52}>
                  {[-36, -12, 12, 36].map(offset => (
                    <line key={offset} x1={window.x - 74} y1={window.y + offset}
                      x2={window.x + 74} y2={window.y + offset}/>
                  ))}
                </g>
              )}
            </g>
            <text x={window.x} y={window.y + 102} textAnchor="middle" fontFamily={SANS}
              fontSize={22} fill={MUTED}>{window.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

const SE_POINTS: Array<[number, number]> = [1, 2, 3, 5, 10, 30, 100, 300, 1000].map(n => {
  const x = 440 + (log10(n) / 3) * 1000;
  const y = 250 + (1 - 1 / Math.sqrt(n)) * 540;
  return [x, y];
});

function StandardError({frame, opacity}: {frame: number; opacity: number}) {
  const curve = easeInOutSine(frameProgress(frame, 1268, 96));
  const marks = fadeIn(frame, 1350, 1390);
  const note18 = fadeIn(frame, 1350, 1390);
  const note4 = fadeIn(frame, 1410, 1450);
  const x3 = 440 + (log10(3) / 3) * 1000;
  const y3 = 250 + (1 - 1 / Math.sqrt(3)) * 540;
  const x1000 = 1440;
  const y1000 = 250 + (1 - 1 / Math.sqrt(1000)) * 540;
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <div style={{
        position: 'absolute', left: 440, top: 148, fontFamily: LATIN, ...NUMERIC_STYLE,
        fontSize: 64, color: IVORY, opacity: fadeIn(frame, 1268, 1306), whiteSpace: 'nowrap',
      }}>SE = σ / √n</div>
      <div style={{
        position: 'absolute', left: 444, top: 218, fontFamily: LATIN, fontSize: 21,
        letterSpacing: '0.2em', color: MUTED, opacity: fadeIn(frame, 1276, 1314), textTransform: 'uppercase',
      }}>standard error</div>
      <ChartFrame x={440} y={250} width={1000} height={540}
        xTicks={[0, 1 / 3, 2 / 3, 1]} xLabels={['1', '10', '100', '1000']}
        yTicks={[0, 0.25, 0.5, 0.75, 1]} yLabels={['0', '0.25', '0.5', '0.75', '1']}
        opacity={0.9}/>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <ChartLine points={SE_POINTS} color={IVORY} width={5} smooth progress={curve}/>
        <ChartMarker x={x3} y={y3} radius={10} color={GOLD} halo opacity={marks}
          label="n = 3" labelColor={GOLD} labelX={x3 - 20} labelY={y3 + 40} align="end"/>
        <ChartMarker x={x1000} y={y1000} radius={10} color={GOLD} halo opacity={marks}
          label="n = 1000" labelColor={GOLD} labelY={y1000 - 34} labelX={x1000 + 6}/>
        <g opacity={note18}>
          <line x1={1520} y1={y3} x2={1520} y2={y1000} stroke={GOLD} strokeWidth={3}
            strokeLinecap="round"/>
          <line x1={1504} y1={y3} x2={1536} y2={y3} stroke={GOLD} strokeWidth={3} strokeLinecap="round"/>
          <line x1={1504} y1={y1000} x2={1536} y2={y1000} stroke={GOLD} strokeWidth={3} strokeLinecap="round"/>
          <text x={1552} y={(y3 + y1000) / 2} fontFamily={LATIN} fontSize={44} fill={GOLD}
            style={{fontVariantNumeric: 'tabular-nums'}}>≈18×</text>
          <text x={1552} y={(y3 + y1000) / 2 + 36} fontFamily={SANS} fontSize={22} fill={MUTED}>误差缩小</text>
        </g>
        <text x={1440} y={196} textAnchor="end" fontFamily={SANS} fontSize={30} fill={GOLD}
          opacity={note4}>n × 4 → 误差 ÷ 2</text>
      </svg>
    </div>
  );
}

function Return({frame, opacity}: {frame: number; opacity: number}) {
  const field = fadeIn(frame, 1506, 1570);
  const title = fadeIn(frame, 1516, 1568);
  const number = fadeIn(frame, 1540, 1580);
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <DotField box={RETURN_BOX} points={FIELD_POINTS} opacity={field * 0.62} reveal={1}
        emphasis={GOLD_POINTS} emphasisOpacity={field}/>
      <BilingualTitle zh="样本" x={140} y={438} size={220}
        opacity={title} ruleWidth={96} ruleProgress={title}/>
      <div style={{
        position: 'absolute', left: 140, top: 690, fontFamily: LATIN, ...NUMERIC_STYLE,
        fontSize: 40, color: GOLD, opacity: number, letterSpacing: '0.02em',
      }}>3 / 1000 = 0.3%</div>
    </div>
  );
}

function MethodNote({frame}: {frame: number}) {
  return (
    <div style={{
      position: 'absolute', right: 48, top: 1008, textAlign: 'right',
      fontFamily: SANS, fontSize: 22, lineHeight: 1.35, color: MUTED,
      opacity: fadeIn(frame, 120, 180) * 0.82,
    }}>
      数学演示：假设观测随机、独立、同分布。
      <div style={{
        fontFamily: LATIN, fontSize: 20, letterSpacing: '0.1em', marginTop: 2,
        textTransform: 'uppercase',
      }}>a math demo: random, independent, identical</div>
    </div>
  );
}

export default function SampleScene({props, width, height, subtitleSafeArea, fps}: CodeSceneProps) {
  const {elapsedSeconds, ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    ready();
  }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  const subtitles = ((props as unknown as Props).screenSubtitles ?? []) as Subtitle[];

  const opening = fadeOut(frame, 156, 180);
  const swings = windowOpacity(frame, 156, 180, 366, 390);
  // 全片唯一硬切：19.93 秒仍是样本量四列，20.00 秒整帧换成三点空场。
  const sampleSize = frame < 600 ? fadeIn(frame, 366, 390) : 0;
  const threeDots = frame >= 600 ? fadeOut(frame, 816, 840) : 0;
  const regression = windowOpacity(frame, 816, 840, 1026, 1050);
  const elephant = windowOpacity(frame, 1026, 1050, 1266, 1290);
  const standardError = windowOpacity(frame, 1266, 1290, 1506, 1530);
  const returned = fadeIn(frame, 1506, 1530);

  return (
    <Stage width={width} height={height}>
      <Opening frame={frame} opacity={opening}/>
      <Swings frame={frame} opacity={swings}/>
      <SampleSize frame={frame} opacity={sampleSize}/>
      <ThreeDots frame={frame} opacity={threeDots}/>
      <Regression frame={frame} opacity={regression}/>
      <Elephant frame={frame} opacity={elephant}/>
      <StandardError frame={frame} opacity={standardError}/>
      <Return frame={frame} opacity={returned}/>
      <MethodNote frame={frame}/>
      <ScreenSubtitle items={subtitles} frame={frame} safeArea={subtitleSafeArea}/>
    </Stage>
  );
}
