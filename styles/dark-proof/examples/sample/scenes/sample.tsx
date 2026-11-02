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
import {hashSeed, samplePath, seededRandom, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import Stage from 'm2v/style/components/stage';
import HeroNumber from 'm2v/style/components/hero-number';
import Counter from 'm2v/style/components/counter';
import DotField, {type DotPoint} from 'm2v/style/components/dot-field';
import {ChartArrow, ChartFrame, ChartLine, ChartMarker} from 'm2v/style/components/proof-chart';
import BilingualTitle from 'm2v/style/components/bilingual-title';
import ScreenSubtitle, {type SubtitleVariant} from 'm2v/style/components/screen-subtitle';
import HandDrawnLine from 'm2v/style/components/hand-drawn-line';
import LightTrail from 'm2v/style/components/light-trail';
import Burst from 'm2v/style/components/burst';
import ShockRing from 'm2v/style/components/shock-ring';
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

/**
 * 大象几何取自 Lucide Lab `elephant`（ISC，`@lucide/lab` 0.7.0）的侧视轮廓：
 * 头部、卷鼻、耳朵、前后腿与眼都来自该图标，只取路径数据，不在运行时依赖图标包。
 * 象牙、尾与眼点为作品补充。图标坐标 24×24，按 `ELE_S` 放大到画面右侧。
 * 来源、版本与许可见作品 SOURCES.md。
 */
const ELE_S = 25;
const ELE_X = 560;
const ELE_Y = 300;
const ELE_PATHS: Array<{d: string; delay: number; width: number}> = [
  // 背、耳外沿与头部右侧。
  {d: 'M14.5 12H14c-2.8 0-5-2.2-5-5V5a2 2 0 0 1 2-2h2c1.5 0 2.8.8 3.4 2H19c1.7 0 3 1.3 3 3v10',
    delay: 10, width: 0.52},
  // 卷鼻。
  {d: 'M14 10a4 4 0 0 0 4 4 4 4 0 0 1 4 4 2 2 0 0 1-4 0', delay: 40, width: 0.5},
  // 前腿内侧。
  {d: 'M10 16v5', delay: 26, width: 0.44},
  // 身体下沿、后腿与前腿外侧。
  {d: 'M18 14a4 4 0 0 0-4 4v3H6v-2.6c0-1.1-.8-2.3-1.7-3C2.9 14.3 2 12.8 2 11c0-3.3 3.1-6 7-6',
    delay: 0, width: 0.52},
  // 后腿外沿。
  {d: 'M2 11v7', delay: 4, width: 0.46},
];
const ELE_TUSKS = [
  'M17.4 14.2C18.5 15 19.1 16 19.2 17.2',
  'M17.8 14.6C18.7 15.3 19.2 16.1 19.3 17',
];
const ELE_EYE = {x: 18, y: 10, r: 0.34};

/**
 * 三个取样窗是同一大象的真实局部放大：窗放在象身右侧，用细引线指向被放大的点，
 * 窗内是同一组路径按 `zoom` 放大后的裁片，不是另画的纹理。
 */
const ELE_CROPS = [
  {label: '耳朵', source: {x: 9.3, y: 7.6}, center: {x: 1376, y: 356}, zoom: 1.55},
  {label: '头部', source: {x: 21.9, y: 17.9}, center: {x: 1632, y: 536}, zoom: 1.55},
  {label: '前腿', source: {x: 14, y: 19.2}, center: {x: 1376, y: 716}, zoom: 1.65},
].map(crop => ({
  ...crop,
  source: {x: ELE_X + crop.source.x * ELE_S, y: ELE_Y + crop.source.y * ELE_S},
}));

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
  const line = easeInOutSine(frameProgress(frame, 626, 74));
  const dissolve = easeInOutSine(frameProgress(frame, 738, 64));
  const lineColor = mixColor(IVORY, EMBER, dissolve);
  const lineOpacity = 1 - dissolve;
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <HandDrawnLine d={TREND} color={lineColor} width={9} progress={line} opacity={lineOpacity}/>
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
  const part = (delay: number) => easeInOutSine(frameProgress(frame, 1028 + delay, 72));
  const eye = fadeIn(frame, 1104, 1150);
  const windows = windowOpacity(frame, 1104, 1140, 1200, 1246);
  const whole = fadeIn(frame, 1194, 1252);
  const figure = (keyPrefix: string) => (
    <g transform={`translate(${ELE_X} ${ELE_Y}) scale(${ELE_S})`}>
      {ELE_PATHS.map((path, index) => (
        <HandDrawnLine key={`${keyPrefix}-${index}`} d={path.d} color={IVORY}
          width={path.width} progress={part(path.delay)} ghostOffset={0.02}/>
      ))}
      {ELE_TUSKS.map((d, index) => (
        <HandDrawnLine key={`${keyPrefix}-tusk-${index}`} d={d} color={IVORY} width={0.3}
          progress={part(54 + index * 6)} ghostOffset={0} freehand={false}/>
      ))}
      <circle cx={ELE_EYE.x} cy={ELE_EYE.y} r={ELE_EYE.r} fill={IVORY} opacity={eye}/>
    </g>
  );
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <BilingualTitle zh="盲人摸象" en="the blind men and the elephant" x={180} y={196} size={60}
        opacity={fadeIn(frame, 1028, 1064)} ruleWidth={64}/>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
        <defs>
          <radialGradient id="sample-elephant-halo">
            <stop offset="0" stopColor={IVORY} stopOpacity={0.16}/>
            <stop offset="1" stopColor={IVORY} stopOpacity={0}/>
          </radialGradient>
          <g id="sample-elephant-figure">{figure('figure')}</g>
          {ELE_CROPS.map((crop, index) => (
            <clipPath id={`sample-window-${index}`} key={index}>
              <circle cx={crop.center.x} cy={crop.center.y} r={82}/>
            </clipPath>
          ))}
        </defs>
        {/* 整体揭示：同一组图标路径的剪影，不是另画一只象。 */}
        <g opacity={whole}>
          <ellipse cx={960} cy={600} rx={400} ry={320} fill="url(#sample-elephant-halo)"/>
          <g transform={`translate(${ELE_X} ${ELE_Y}) scale(${ELE_S})`} fill={IVORY} opacity={0.14}>
            {ELE_PATHS.map((path, index) => <path key={index} d={path.d}/>)}
          </g>
        </g>
        {/* 引线画在象身之下：只在象与取样窗之间的空场露出，不切断轮廓。 */}
        <g opacity={windows}>
          {ELE_CROPS.map(crop => {
            const {source, center} = crop;
            const distance = Math.hypot(center.x - source.x, center.y - source.y);
            const dx = (center.x - source.x) / distance;
            const dy = (center.y - source.y) / distance;
            return (
              <line key={`lead-${crop.label}`} x1={source.x} y1={source.y}
                x2={center.x - dx * 90} y2={center.y - dy * 90}
                stroke={IVORY} strokeWidth={1.4} opacity={0.28}/>
            );
          })}
        </g>
        <use href="#sample-elephant-figure"/>
        {ELE_CROPS.map((crop, index) => (
          <g key={crop.label} opacity={windows}>
            <circle cx={crop.source.x} cy={crop.source.y} r={5} fill={IVORY} opacity={0.65}/>
            <g clipPath={`url(#sample-window-${index})`}>
              <use href="#sample-elephant-figure"
                transform={`translate(${crop.center.x} ${crop.center.y}) scale(${crop.zoom}) translate(${-crop.source.x} ${-crop.source.y})`}/>
            </g>
            <circle cx={crop.center.x} cy={crop.center.y} r={82} fill="none" stroke={IVORY}
              strokeWidth={2} opacity={0.3}/>
            <text x={crop.center.x} y={crop.center.y + 108} textAnchor="middle" fontFamily={SANS}
              fontSize={26} fill={MUTED}>{crop.label}</text>
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
  const title = fadeIn(frame, 1516, 1568);
  const number = fadeIn(frame, 1540, 1580);
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      <BilingualTitle zh="样本" x={140} y={438} size={220}
        opacity={title} ruleWidth={96} ruleProgress={title}/>
      <div style={{
        position: 'absolute', left: 140, top: 690, fontFamily: LATIN, ...NUMERIC_STYLE,
        fontSize: 40, color: GOLD, opacity: number, letterSpacing: '0.02em',
      }}>3 / 1000 = 0.3%</div>
    </div>
  );
}

type AnchorPoint = {x: number; y: number};
type AnchorState = {
  points: AnchorPoint[];
  radius: number;
  opacity: number;
  trail?: {from: AnchorPoint[]; to: AnchorPoint[]; progress: number};
};

const FIELD_GOLD: AnchorPoint[] = GOLD_POINTS.map(point => ({
  x: FIELD_BOX.x + point.x * FIELD_BOX.width,
  y: FIELD_BOX.y + point.y * FIELD_BOX.height,
}));
const DISC_TOP: AnchorPoint[] = [
  {x: 720, y: 628}, {x: 960, y: 628}, {x: 1200, y: 628},
];
const N3_POINTS: AnchorPoint[] = COLUMN_POINTS[0].points.slice(0, 3)
  .map(point => ({x: point.x * W, y: point.y * H}));
const TREND_POINTS: AnchorPoint[] = THREE_POINTS.map(([x, y]) => ({x, y}));
const TREND_SAMPLED = samplePath(TREND, 80);
const WINDOW_POINTS: AnchorPoint[] = ELE_CROPS.map(crop => ({x: crop.center.x, y: crop.center.y}));
const seX = (n: number) => 440 + (log10(n) / 3) * 1000;
const seY = (n: number) => 250 + (1 - 1 / Math.sqrt(n)) * 540;
const SE_MARKERS: AnchorPoint[] = [
  {x: seX(3), y: seY(3)},
  {x: seX(1000), y: seY(1000)},
  {x: 1520, y: (seY(3) + seY(1000)) / 2},
];

function lerpPoints(from: AnchorPoint[], to: AnchorPoint[], progress: number): AnchorPoint[] {
  return from.map((point, index) => ({
    x: lerp(point.x, to[index].x, progress),
    y: lerp(point.y, to[index].y, progress),
  }));
}

function anchorState(frame: number): AnchorState {
  if (frame < 92) return {points: FIELD_GOLD, radius: 13, opacity: 0};
  if (frame < 156) return {points: FIELD_GOLD, radius: 13, opacity: 1};
  if (frame < 180) {
    const progress = easeInOutSine(frameProgress(frame, 156, 24));
    return {
      points: lerpPoints(FIELD_GOLD, DISC_TOP, progress), radius: lerp(13, 7, progress),
      opacity: 1, trail: {from: FIELD_GOLD, to: DISC_TOP, progress},
    };
  }
  if (frame < 366) return {points: DISC_TOP, radius: 7, opacity: 1};
  if (frame < 390) {
    const progress = easeInOutSine(frameProgress(frame, 366, 24));
    return {
      points: lerpPoints(DISC_TOP, N3_POINTS, progress), radius: lerp(7, 7, progress),
      opacity: 1, trail: {from: DISC_TOP, to: N3_POINTS, progress},
    };
  }
  if (frame < 600) return {points: N3_POINTS, radius: 7, opacity: 1};
  // 唯一硬切：600 帧整帧从 n=3 样本点跳到趋势点，不给形变轨迹。
  if (frame < 816) return {points: TREND_POINTS, radius: 11, opacity: 1};
  if (frame < 840) return {points: TREND_POINTS, radius: 11, opacity: fadeOut(frame, 816, 840)};
  if (frame < 1026) return {points: TREND_POINTS, radius: 11, opacity: 0};
  if (frame < 1050) return {points: WINDOW_POINTS, radius: 72, opacity: fadeIn(frame, 1026, 1050)};
  if (frame < 1266) return {points: WINDOW_POINTS, radius: 72, opacity: 1};
  if (frame < 1290) {
    const progress = easeInOutSine(frameProgress(frame, 1266, 24));
    return {
      points: lerpPoints(WINDOW_POINTS, SE_MARKERS, progress), radius: lerp(72, 7, progress),
      opacity: 1, trail: {from: WINDOW_POINTS, to: SE_MARKERS, progress},
    };
  }
  if (frame < 1506) return {points: SE_MARKERS, radius: 7, opacity: 1};
  if (frame < 1530) {
    const progress = easeInOutSine(frameProgress(frame, 1506, 24));
    return {
      points: lerpPoints(SE_MARKERS, FIELD_GOLD, progress), radius: lerp(7, 13, progress),
      opacity: 1, trail: {from: SE_MARKERS, to: FIELD_GOLD, progress},
    };
  }
  return {points: FIELD_GOLD, radius: 13, opacity: 1};
}

function FieldAnchor({frame}: {frame: number}) {
  if (frame < 180) {
    const fieldIn = fadeIn(frame, 78, 138);
    const reveal = easeInOutSine(frameProgress(frame, 88, 76));
    const toSwings = easeInOutSine(frameProgress(frame, 156, 24));
    return (
      <DotField box={FIELD_BOX} points={FIELD_POINTS}
        opacity={lerp(fieldIn * 0.62, 0.06, toSwings)} reveal={reveal}/>
    );
  }
  if (frame < 366) return <DotField box={FIELD_BOX} points={FIELD_POINTS} opacity={0.06} reveal={1}/>;
  if (frame < 390) {
    const out = easeInOutSine(frameProgress(frame, 366, 24));
    return <DotField box={FIELD_BOX} points={FIELD_POINTS} opacity={lerp(0.06, 0, out)} reveal={1}/>;
  }
  if (frame < 700) return null;
  if (frame < 840) {
    const inField = fadeIn(frame, 700, 756);
    const out = fadeOut(frame, 816, 840);
    return (
      <DotField box={{x: 470, y: 250, width: 980, height: 540}} points={FIELD_POINTS}
        opacity={inField * out * 0.34} reveal={1} radius={3}/>
    );
  }
  if (frame < 1506) return null;
  const inReturn = fadeIn(frame, 1506, 1570);
  return <DotField box={RETURN_BOX} points={FIELD_POINTS} opacity={inReturn * 0.62} reveal={1}/>;
}

function GoldAnchor({frame}: {frame: number}) {
  const state = anchorState(frame);
  if (state.opacity <= 0) return null;
  const ring = state.radius > 20;
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
      <defs>
        <radialGradient id="sample-gold-glow">
          <stop offset="0" stopColor={T.light.core} stopOpacity={0.7}/>
          <stop offset="0.45" stopColor={GOLD} stopOpacity={0.28}/>
          <stop offset="1" stopColor={GOLD} stopOpacity={0}/>
        </radialGradient>
      </defs>
      <g opacity={state.opacity} style={{mixBlendMode: 'screen'}}>
        {state.points.map((point, index) => (
          <g key={index}>
            <circle cx={point.x} cy={point.y} r={Math.max(18, state.radius * 1.8)}
              fill="url(#sample-gold-glow)" opacity={ring ? 0.2 : 0.45}/>
            {ring ? (
              <circle cx={point.x} cy={point.y} r={state.radius} fill="none"
                stroke={GOLD} strokeWidth={2} opacity={0.82}/>
            ) : null}
            <circle cx={point.x} cy={point.y} r={ring ? 5 : state.radius} fill={GOLD}/>
          </g>
        ))}
      </g>
      {state.trail ? state.trail.from.map((from, index) => (
        <LightTrail key={`anchor-trail-${index}`} points={[from, state.trail!.to[index]]}
          progress={state.trail!.progress} length={0.55} samples={6} width={6}
          dust={0} glow={2.8} opacity={0.85}/>
      )) : null}
    </svg>
  );
}

function LightEvents({frame}: {frame: number}) {
  const opening = easeInOutSine(frameProgress(frame, 62, 70));
  const line = easeInOutSine(frameProgress(frame, 626, 74));
  const arrows = easeInOutSine(frameProgress(frame, 926, 90));
  const curve = easeInOutSine(frameProgress(frame, 1268, 96));
  const openingOpacity = frame < 62 ? 0 : frame < 132 ? 0.7 : Math.max(0, 1 - (frame - 132) / 18) * 0.7;
  const lineOpacity = frame < 626 ? 0 : frame < 700 ? 0.8 : Math.max(0, 1 - (frame - 700) / 24) * 0.8;
  const arrowOpacity = frame < 926 ? 0 : frame < 1016 ? 0.7 : Math.max(0, 1 - (frame - 1016) / 18) * 0.7;
  const curveOpacity = frame < 1268 ? 0 : frame < 1364 ? 0.8 : Math.max(0, 1 - (frame - 1364) / 24) * 0.8;
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
      <LightTrail points={[{x: 960, y: 520}, {x: 360, y: 500}]} progress={opening}
        length={0.5} width={9} samples={8} dust={3} opacity={openingOpacity}/>
      <LightTrail points={TREND_SAMPLED} progress={line} length={0.24} width={7}
        samples={12} dust={3} opacity={lineOpacity}/>
      <LightTrail points={[{x: 660, y: 360}, {x: 850, y: 410}, {x: 1040, y: 464}]}
        progress={arrows} length={0.3} width={6} samples={8} dust={0} opacity={arrowOpacity}/>
      <LightTrail points={[{x: 660, y: 608}, {x: 850, y: 580}, {x: 1040, y: 550}]}
        progress={arrows} length={0.3} width={6} samples={8} dust={0} opacity={arrowOpacity}/>
      <LightTrail points={SE_POINTS.map(([x, y]) => ({x, y}))} progress={curve}
        length={0.17} width={7} samples={14} dust={3} opacity={curveOpacity}/>
      <Burst origin={{x: 1200, y: 690}} progress={frameProgress(frame, 235, 22)}
        count={10} distance={46} rings={1} ringTravel={52}/>
      <Burst origin={{x: 960, y: 690}} progress={frameProgress(frame, 285, 22)}
        count={10} distance={46} rings={1} ringTravel={52}/>
      <Burst origin={{x: 1200, y: 690}} progress={frameProgress(frame, 335, 22)}
        count={10} distance={46} rings={1} ringTravel={52}/>
      <ShockRing origin={{x: 960, y: 540}} progress={frameProgress(frame, 600, 20)}
        count={1} travel={220} thickness={2.5} dashes="0.03 0.02"/>
      <Burst origin={{x: 960, y: 560}} progress={frameProgress(frame, 738, 64)}
        count={18} distance={150} rings={2} ringTravel={180}/>
      <Burst origin={{x: 960, y: 450}} progress={frameProgress(frame, 1194, 58)}
        count={18} distance={180} rings={2} ringTravel={220}/>
      {WINDOW_POINTS.map((point, index) => (
        <g key={`window-ring-${index}`}>
          <ShockRing origin={point} progress={frameProgress(frame, 1106, 70)}
            count={1} travel={90} thickness={2}/>
          <Burst origin={point} progress={frameProgress(frame, 1106, 70)}
            count={8} distance={42} rings={0}/>
        </g>
      ))}
      <Burst origin={{x: 1440, y: 773}} progress={frameProgress(frame, 1350, 45)}
        count={18} distance={130} rings={2} ringTravel={160}/>
      <Burst origin={{x: 1150, y: 530}} progress={frameProgress(frame, 1580, 60)}
        count={14} distance={90} rings={1} ringTravel={120}/>
    </svg>
  );
}

const SUBTITLE_VARIANTS: Record<number, SubtitleVariant> = {
  14: {enter: 'rise', exit: 'drift', englishDelayFrames: 14},
  192: {enter: 'rise', exit: 'drift', englishDelayFrames: 10},
  402: {enter: 'settle', exit: 'mask', englishDelayFrames: 8},
  606: {enter: 'wipe', exit: 'drift', englishDelayFrames: 12},
  726: {enter: 'rise', exit: 'dissolve', englishDelayFrames: 14},
  852: {enter: 'settle', exit: 'drift', englishDelayFrames: 12},
  936: {enter: 'rise', exit: 'drift', englishDelayFrames: 10},
  1062: {enter: 'wipe', exit: 'mask', englishDelayFrames: 12},
  1194: {enter: 'settle', exit: 'drift', englishDelayFrames: 10},
  1302: {enter: 'rise', exit: 'drift', englishDelayFrames: 12},
  1416: {enter: 'rise', exit: 'drift', englishDelayFrames: 12},
  1542: {enter: 'settle', exit: 'drift', englishDelayFrames: 10},
  1656: {enter: 'rise', exit: 'dissolve', englishDelayFrames: 12},
};
const SUBTITLE_EMPHASIS = /3|1000|33|18|0\.3%|四倍|局部|整体|回归|极端|平均|三个点|一条线|样本做大/;

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

  // 转场不叠两张全亮画面：旧层 14 帧快速退场，新层晚 2 帧、用 14 帧进入。
  // 旧层 8 帧内降到 0.15 以下，交叉淡化总长 16 帧，避免双重曝光也不留下重影。
  const leave = (start: number) => 1 - easeOutCubic(frameProgress(frame, start, 14));
  const enter = (start: number) => easeInOutSine(frameProgress(frame, start + 2, 14));
  const opening = leave(156);
  const swings = enter(156) * leave(366);
  // 全片唯一硬切：19.93 秒仍是样本量四列，20.00 秒整帧换成三点空场。
  const sampleSize = frame < 600 ? enter(366) : 0;
  const threeDots = frame >= 600 ? leave(816) : 0;
  const regression = enter(816) * leave(1026);
  const elephant = enter(1026) * leave(1266);
  const standardError = enter(1266) * leave(1506);
  const returned = enter(1506);

  return (
    <Stage width={width} height={height}>
      <FieldAnchor frame={frame}/>
      <Opening frame={frame} opacity={opening}/>
      <Swings frame={frame} opacity={swings}/>
      <SampleSize frame={frame} opacity={sampleSize}/>
      <ThreeDots frame={frame} opacity={threeDots}/>
      <Regression frame={frame} opacity={regression}/>
      <Elephant frame={frame} opacity={elephant}/>
      <StandardError frame={frame} opacity={standardError}/>
      <Return frame={frame} opacity={returned}/>
      <GoldAnchor frame={frame}/>
      <LightEvents frame={frame}/>
      <MethodNote frame={frame}/>
      <ScreenSubtitle items={subtitles} frame={frame} safeArea={subtitleSafeArea}
        variants={SUBTITLE_VARIANTS} emphasis={SUBTITLE_EMPHASIS}/>
    </Stage>
  );
}
