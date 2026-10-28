/**
 * 《鸽子的迷信》示例：食物按时间来，它却碰巧在转圈，于是它接着转。
 *
 * 选题与分镜按外部参考项目已登记的 pigeon_B 分镜表重写；本文件是独立实现——
 * 鸽子、箱子、计时器与食槽的形体、比例与画法都由本文件自行决定，
 * 不复制上游 `film.js` 的任何函数、路径数据或调色常量。
 *
 * 时间轴：录制按幕挂载，`elapsedSeconds` 是幕内时间。所以每幕在
 * `props.clock.startSeconds` 里声明自己在全片时间轴上的起点，计时器用
 * 「幕起点 + 幕内时间」，第 15 秒与第 30 秒各掉一次食物——跨幕连续。
 */
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps, painter} from 'm2v/code-scene';
import FableStage from 'm2v/style/components/fable-stage';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import SceneNote from 'm2v/style/components/scene-note';
import TopLine from 'm2v/style/components/top-line';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';

type Chapter = {id: string; year: string; place: string; topLine: string};
type Clock = {startSeconds: number};
type Gauge = {value: number; startValue: number; object: string};
type Subtitle = {startFrame: number; endFrame: number; text: string};
type Props = {chapter: Chapter; clock: Clock; gauge: Gauge; screenSubtitles: Subtitle[]};

type P = InstanceType<typeof painter.Painter>;

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {const t = clamp(value); return t * t * (3 - 2 * t);};
const round = (value: number, digits = 2) => Number(value.toFixed(digits));

/** 喂食间隔与全片两次喂食的时刻。 */
const FEED_INTERVAL = 15;
const FEED_TIMES = [15, 30];
const DROP_SECONDS = 1.1;

// 本示例自己的配色：暖木箱、米色墙、谷黄、橙红轨迹。取自 tokens 的场景盘，不引入新语义。
const INK = '#3A2A22';
const FLOOR = '#C8A874';
const WALL = '#EFE2C4';
const PLANK = '#8A6242';
const FRAME_WOOD = '#6B4A30';
const GRAIN_COLOR = '#E9B93A';
const TRACK = '#D9562B';
const BIRD = '#8C9DB4';
const BIRD_DARK = '#5E6E86';
const BIRD_BEAK = '#33333C';
// 本包不带字体；画布文字用宿主已注册的 `M2V Sans`。`sans` 不是合法族名，会回退到浏览器默认。
const SANS = '"M2V Sans", "Noto Sans SC", sans-serif';

/**
 * 鸟：用一条闭合轮廓画出身体与头，再用两条折线画翅膀与腿。
 * 比例是本示例自己的：身体长约为高的 1.5 倍，头在右前上方。
 */
function bird(P: P, x: number, y: number, scale: number, pose: {
  facing?: number; peck?: number; flap?: number; bob?: number; alpha?: number;
}) {
  const {facing = 1, peck = 0, flap = 0, bob = 0, alpha = 1} = pose;
  P.group({alpha, at: [x, y], scale: [facing * scale, scale]}, () => {
    P.ellipse(0, 2, 70, 12, {fill: '#000000', alpha: 0.2});
    // 腿：两条折线，膝弯在中点
    for (const offset of [-16, 16]) {
      P.poly([[offset, -30], [offset - 3, -14], [offset - 12, 0]], {color: TRACK, width: 5});
      P.line(offset - 12, 0, offset - 24, 0, {color: TRACK, width: 4});
    }
    // 身体：一条闭合轮廓（尾 → 背 → 头 → 胸 → 腹）
    P.group({rotate: peck * 0.5}, () => {
      P.poly([
        [-96, -74], [-58, -96], [4, -100], [44, -116], [70, -140],
        [82, -120], [70, -96], [46, -70], [10, -46], [-42, -40], [-86, -56],
      ], {fill: BIRD, close: true});
      // 翅膀：一片叠在身体上的深色椭圆，随扑翅抬起
      P.group({at: [-8, -74], rotate: -flap * 0.9}, () => {
        P.ellipse(-6, 4, 46, 26, {fill: BIRD_DARK, rotate: -0.2});
        P.line(-40, 12, 22, 12, {color: '#3F4A5E', width: 5});
      });
      // 头：与身体轮廓相接的小圆，眼睛与喙各一
      const headY = -140 + bob * 7;
      P.circle(66, headY, 22, {fill: BIRD});
      P.poly([[84, headY - 2], [104, headY + 4], [84, headY + 9]], {fill: BIRD_BEAK, close: true});
      P.circle(72, headY - 6, 6, {fill: '#E8842A'});
      P.circle(72, headY - 6, 2.6, {fill: '#1E1A1A'});
    });
  });
}

/**
 * 计时器：一圈 15 秒，但画法是自己的一套——环形刻度 + 走过的弧 + 一个端点圆点，
 * 不用指针与扇区。读数显示剩余秒数，跨幕连续。
 */
function feederTimer(P: P, x: number, y: number, radius: number, globalSeconds: number, alpha = 1) {
  const phase = ((globalSeconds % FEED_INTERVAL) + FEED_INTERVAL) % FEED_INTERVAL;
  const ratio = phase / FEED_INTERVAL;
  P.group({alpha}, () => {
    P.circle(x, y, radius, {fill: '#FFF8E6', alpha: 0.94});
    P.circle(x, y, radius, {color: FRAME_WOOD, width: 4});
    // 15 个刻度，每 5 秒一个粗刻度
    for (let index = 0; index < FEED_INTERVAL; index += 1) {
      const angle = -Math.PI / 2 + (index / FEED_INTERVAL) * Math.PI * 2;
      const inner = radius * (index % 5 === 0 ? 0.68 : 0.78);
      P.line(x + Math.cos(angle) * inner, y + Math.sin(angle) * inner,
        x + Math.cos(angle) * radius * 0.9, y + Math.sin(angle) * radius * 0.9,
        {color: index % 5 === 0 ? INK : '#9A8564', width: index % 5 === 0 ? 4 : 2});
    }
    // 走过的弧：从顶端顺时针到当前时刻
    const steps = 48;
    for (let index = 0; index < Math.round(steps * ratio); index += 1) {
      const from = -Math.PI / 2 + (index / steps) * Math.PI * 2;
      const to = -Math.PI / 2 + ((index + 1) / steps) * Math.PI * 2;
      P.line(x + Math.cos(from) * radius * 0.55, y + Math.sin(from) * radius * 0.55,
        x + Math.cos(to) * radius * 0.55, y + Math.sin(to) * radius * 0.55,
        {color: TRACK, width: 7});
    }
    const tipAngle = -Math.PI / 2 + ratio * Math.PI * 2;
    P.circle(x + Math.cos(tipAngle) * radius * 0.55, y + Math.sin(tipAngle) * radius * 0.55,
      9, {fill: TRACK});
    const remain = Math.max(0, Math.ceil(FEED_INTERVAL - phase));
    P.text(String(remain), x, y + 6, {size: radius * 0.42, color: INK, font: SANS, align: 'center'});
    P.text('秒', x, y + radius * 0.4, {size: radius * 0.16, color: '#8A7554', font: SANS, align: 'center'});
  });
}

/** 箱内：四面木板 + 米色墙面 + 右侧带盖的食槽。几何由本文件决定。 */
function boxRoom(P: P, width: number, height: number, drop: number) {
  P.rect(0, 0, width, height, {fill: FRAME_WOOD});
  P.rect(64, 54, width - 128, height - 300, {fill: WALL});
  for (let index = 1; index < 8; index += 1) {
    P.line(64, 54 + index * ((height - 300) / 8), width - 64, 54 + index * ((height - 300) / 8),
      {color: '#D8C6A0', width: 2});
  }
  P.rect(64, height - 246, width - 128, 62, {fill: FLOOR});
  P.rect(0, height - 184, width, 184, {fill: PLANK, alpha: 0.55});
  // 食槽：墙面开一个投食口，下方是一个斜口盘
  const fx = width * 0.72;
  const fy = height * 0.36;
  const opening = drop > 0 ? Math.min(1, Math.min(drop * 5, (1 - drop) * 4)) : 0;
  P.rect(fx, fy, 240, 132, {fill: '#4A3A2C'});
  P.rect(fx + 12, fy + 12, 216, Math.max(0, 108 * (1 - opening)), {fill: '#B08F63'});
  P.poly([[fx - 26, fy + 158], [fx + 266, fy + 158], [fx + 232, fy + 214], [fx + 8, fy + 214]],
    {fill: '#4A3A2C', close: true});
  if (drop <= 0) return;
  for (let index = 0; index < 14; index += 1) {
    const k = clamp(drop * 2.4 - index * 0.05);
    if (k <= 0) break;
    const gx = fx + 40 + ((index * 41) % 160);
    const gy = fy + 70 + smooth(k) * 120 + (index % 2) * 8;
    P.circle(gx, gy, 8, {fill: GRAIN_COLOR, alpha: 1});
  }
}

/** 转圈轨迹：绕鸟一圈的虚线椭圆，进度随幕内时间推进。 */
function turnTrack(P: P, x: number, y: number, radiusX: number, radiusY: number, progress: number) {
  if (progress <= 0) return;
  const steps = 40;
  const drawn = Math.round(steps * clamp(progress));
  for (let index = 0; index < drawn; index += 1) {
    const from = -Math.PI / 2 + (index / steps) * Math.PI * 2;
    const to = -Math.PI / 2 + ((index + 1) / steps) * Math.PI * 2;
    if (index % 2) continue;
    P.line(x + Math.cos(from) * radiusX, y + Math.sin(from) * radiusY,
      x + Math.cos(to) * radiusX, y + Math.sin(to) * radiusY,
      {color: TRACK, width: 8, alpha: 0.8});
  }
}

/** 全片时间轴上的「这一秒离上一次喂食多久」。 */
function feedPhase(globalSeconds: number): {phase: number; drop: number} {
  const since = globalSeconds - FEED_TIMES.filter(t => t <= globalSeconds).slice(-1)[0];
  if (!Number.isFinite(since) || since < 0) return {phase: ((globalSeconds % FEED_INTERVAL) + FEED_INTERVAL) % FEED_INTERVAL, drop: 0};
  const phase = globalSeconds % FEED_INTERVAL;
  return {phase, drop: since < DROP_SECONDS ? since / DROP_SECONDS : 0};
}

export default function Pigeon(props: CodeSceneProps & Props) {
  const {width, height, fps, subtitleSafeArea, props: values} = props;
  const {chapter, clock, gauge, screenSubtitles} = values;
  const {elapsedSeconds, ready} = useSceneContext();
  const frame = Math.round(elapsedSeconds * fps);
  // 逐幕挂载：幕内时间 + 本幕在全片时间轴上的起点 = 全片时间。
  const globalSeconds = (clock?.startSeconds ?? 0) + elapsedSeconds;
  const {drop} = feedPhase(globalSeconds);
  const inside = chapter.id !== 'box';
  const turning = chapter.id === 'repeat' || chapter.id === 'again';

  useEffect(() => {
    let active = true;
    document.fonts.ready.then(() => {if (active) ready();});
    return () => {active = false;};
  }, [ready]);

  return (
    <div style={{position: 'absolute', inset: 0, width, height}}>
      <FableStage scene={inside ? 'desk' : 'night'} width={width} height={height} horizon={0.74}/>
      <painter.PainterCanvas width={width} height={height} bloom={0.3} grain={0.06} seed={chapter.id.length + 5}
        paint={(P) => {
          P.clear('rgba(0,0,0,0)');
          if (!inside) {
            // 场景：实验室桌上的木箱，灯从上方打下来
            P.rect(0, 0, width, height, {fill: '#2A2430', alpha: 0.5});
            const bx = width * 0.08;
            const by = height * 0.13;
            const bw = width * 0.58;
            const bh = height * 0.62;
            P.rect(bx - 16, by - 16, bw + 32, bh + 32, {fill: FRAME_WOOD});
            P.rect(bx, by, bw, bh, {fill: WALL});
            P.rect(bx, by + bh - 62, bw, 62, {fill: FLOOR});
            P.path(`M ${bx + bw / 2 - 46},${by - 128} L ${bx + bw / 2 + 46},${by - 128} `
              + `L ${bx + bw / 2 + 208},${by + bh} L ${bx + bw / 2 - 208},${by + bh} Z`,
              {fill: '#FFE7B0', alpha: 0.07});
            P.ellipse(bx + bw / 2, by - 134, 34, 10, {fill: '#FFE7B0', alpha: 0.55});
            bird(P, bx + bw * 0.42, by + bh - 78, 0.8, {
              peck: Math.sin(globalSeconds * 2.4) > 0.4 ? 0.7 : 0.1,
              bob: Math.sin(globalSeconds * 2.9) * 0.4,
            });
            feederTimer(P, width * 0.84, height * 0.33, 86, globalSeconds, 0.95);
          } else {
            boxRoom(P, width, height, drop);
            const floor = height * 0.71;
            const cx = width * 0.46;
            const sway = Math.sin(globalSeconds * 1.1) * 70 + Math.sin(globalSeconds * 2.7) * 22;
            const spin = turning ? Math.sin(globalSeconds * 2.1) * 0.9 : 0;
            if (turning) turnTrack(P, cx, floor + 4, 168, 46, (globalSeconds - 19) / 2.4);
            bird(P, cx + sway, floor, 1.0, {
              facing: Math.cos(spin) >= 0 ? 1 : -1,
              peck: chapter.id === 'coincide' ? 0.8 : Math.abs(Math.sin(globalSeconds * 2.2)) * 0.35,
              flap: chapter.id === 'coincide' && drop > 0.2 ? 0.5 : 0,
              bob: Math.sin(globalSeconds * 3.2) * 0.35,
            });
            feederTimer(P, width * 0.84, height * 0.26, 84, globalSeconds, 0.95);
          }
          if (drop > 0) P.glow(width * 0.72 + 120, height * 0.36 + 190, 110, '#FFD27A', 0.32 * drop);
        }}/>

      <SceneNote year={chapter.year} place={chapter.place}/>
      <InstinctGauge value={gauge.value} startValue={gauge.startValue} object={gauge.object}
        frame={frame} startFrame={10} durationFrames={64}/>
      <TopLine text={chapter.topLine} frame={frame} startFrame={12}
        color={inside ? INK : '#EEC672'}/>
      <ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={subtitleSafeArea} fps={fps}/>
    </div>
  );
}
