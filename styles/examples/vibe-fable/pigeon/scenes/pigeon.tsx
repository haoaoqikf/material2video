/**
 * 《鸽子的迷信》示例：食物按时间来，它却碰巧在转圈，于是它接着转。
 *
 * 选题与分镜按外部参考项目已登记的 pigeon_B 分镜表重写；本文件是独立实现——
 * 鸽子、箱子、计时器与食槽的形体、比例与画法都由本文件自行决定，
 * 不复制上游 `film.js` 的任何函数、路径数据或调色常量。
 *
 * **一个箱子，一台摄影机。** 箱子内部是一个固定的房间：墙面、地板、食槽与墙上的
 * 计时器各有自己的房间坐标。六幕只是这台摄影机的六段行程——全景、计时器特写、
 * 中景、食槽近景、慢推、计时器前置。房间不动，动的是镜头，所以观众始终在同一个
 * 空间里，而不是看六张构图不同的插画。
 *
 * 时间轴：录制按幕挂载，`elapsedSeconds` 是幕内时间。每幕声明
 * `content.props.capture.timebase: "global"`，录制上下文据此提供 `globalSeconds`
 * （幕起点 + 幕内时间）；计时器、喂食状态与鸽子行为都读同一个全局时间，
 * 第 15 秒与第 30 秒各掉一次食物——跨幕连续。
 */
import {useEffect} from 'react';
import {createSceneEvents, useSceneContext, type CodeSceneProps, painter} from 'm2v/code-scene';
import FableStage from 'm2v/style/components/fable-stage';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import SceneNote from 'm2v/style/components/scene-note';
import TopLine from 'm2v/style/components/top-line';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';

type Chapter = {id: string; year: string; place: string; topLine: string};
type Gauge = {value: number; startValue: number; object: string};
type Subtitle = {startFrame: number; endFrame: number; text: string};
type Props = {chapter: Chapter; gauge: Gauge; screenSubtitles: Subtitle[]};

type P = InstanceType<typeof painter.Painter>;
type Vec = [number, number];

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {const t = clamp(value); return t * t * (3 - 2 * t);};

/** 喂食间隔与全片两次喂食的时刻。 */
const FEED_INTERVAL = 15;
const FEED_TIMES = [15, 30];
const DROP_SECONDS = 1.2;

/**
 * 本色板取自 tokens 的场景盘，只在这里展开成具体的房间色。
 *
 * 墙面刻意比设计稿的米色暗一档：浅米色在辉光叠加后会顶到 255，
 * 参考片的墙是 183 左右的中间调，留得住阴影与木纹。
 */
const INK = '#3A2A22';
const WALL = '#C9B48C';
const WALL_LINE = '#BBA57C';
const FLOOR = '#A8875C';
const PLANK = '#6B4A30';
const FRAME_WOOD = '#5A3E28';
const GRAIN = '#E9B93A';
const TRACK = '#D9562B';
const BIRD_BODY = '#8C9DB4';
const BIRD_TAIL = '#5E6E86';
const BIRD_WING = '#6F7D96';
const BIRD_WING_LINE = '#3F4A5E';
const BIRD_NECK_GREEN = '#4E9A7E';
const BIRD_NECK_PURPLE = '#8A62A8';
const BIRD_BEAK = '#33333C';
const BIRD_LEG = '#D9707E';
// 本包不带字体；画布文字用宿主已注册的 `M2V Sans`。
const SANS = '"M2V Sans", "Noto Sans SC", sans-serif';

// ---------------------------------------------------------------- 房间坐标

/** 房间是固定的 1920×1080；所有物件只写一次坐标，镜头负责取景。 */
const ROOM_W = 1920;
const ROOM_H = 1080;
const WALL_INSET_X = 64;
const WALL_TOP = 54;
const WALL_BOTTOM = 866;
const FLOOR_Y = 838;
const FEEDER: Vec = [1520, 400];
const TIMER: Vec = [1690, 250];
const TIMER_R = 96;

/**
 * 六幕的镜头表。`scale` 是「房间 1 单位画多少像素」，焦点是取景中心。
 *
 * 与参考片对齐：全景 → 计时器特写 → 中景 → 食槽近景 → 中景慢推 → 计时器前置。
 * 每幕在幕内缓动，幕间不硬切——观众不会察觉「换了一个镜头」，只会觉得镜头在走。
 */
type Shot = {from: {scale: number; focus: Vec}; to: {scale: number; focus: Vec}};
const SHOTS: Record<string, Shot> = {
  // 全景：计时器与食槽同框，鸽子靠动作读。
  feeder: {from: {scale: 1.26, focus: [1160, 520]}, to: {scale: 1.36, focus: [1210, 505]}},
  // 中景：鸽子是画面唯一的大主体，食槽与计时器留在右侧。
  wander: {from: {scale: 1.5, focus: [1180, 555]}, to: {scale: 1.6, focus: [1200, 555]}},
  // 近景：鸽子在食槽边啄食。
  coincide: {from: {scale: 1.62, focus: [1230, 590]}, to: {scale: 1.74, focus: [1245, 595]}},
  // 中景：转圈轨迹完整落在画面里。
  repeat: {from: {scale: 1.46, focus: [1170, 570]}, to: {scale: 1.56, focus: [1170, 570]}},
  // 计时器前置：计时器在上、鸽子在下。
  again: {from: {scale: 1.4, focus: [1190, 545]}, to: {scale: 1.5, focus: [1210, 552]}},
};

function shotAt(chapterId: string, progress: number): {scale: number; focus: Vec} {
  const shot = SHOTS[chapterId];
  if (!shot) return {scale: 1, focus: [ROOM_W / 2, ROOM_H / 2]};
  const t = smooth(progress);
  return {
    scale: shot.from.scale + (shot.to.scale - shot.from.scale) * t,
    focus: [shot.from.focus[0] + (shot.to.focus[0] - shot.from.focus[0]) * t,
      shot.from.focus[1] + (shot.to.focus[1] - shot.from.focus[1]) * t],
  };
}

// ---------------------------------------------------------------- 形体

/**
 * 一只鸽子：色块拼成，不描边。
 *
 * 从后往前叠：影子、腿、尾、身、翅、颈的两个色环、头、喙、眼。层数与参考一致，
 * 所以它是一只有体积的鸟，而不是一块剪影。比例按身体的长度约为高度的 1.5 倍。
 */
function bird(P: P, x: number, y: number, scale: number, pose: {
  facing?: number; turn?: number; peck?: number; flap?: number; bob?: number; alpha?: number;
}) {
  const {facing = 1, turn, peck = 0, flap = 0, bob = 0, alpha = 1} = pose;
  // 转向时横向压扁身体，和参考片的「转身」读法一致；未给 turn 时保持原朝向。
  const cosine = turn === undefined ? facing : Math.cos(turn);
  const width = turn === undefined ? facing : (Math.abs(cosine) < 0.32 ? 0.32 * (cosine < 0 ? -1 : 1) : cosine);
  P.group({alpha, at: [x, y], scale: [width * scale, scale]}, () => {
    // 影子：贴地的一圈，让鸟站得住。
    P.ellipse(0, 6, 66, 12, {fill: '#000000', alpha: 0.22});
    // 腿：两段折线加脚掌。
    for (const offset of [-18, 16]) {
      P.poly([[offset, -34], [offset - 4, -18], [offset - 14, 0]], {color: BIRD_LEG, width: 6});
      P.line(offset - 14, 0, offset - 28, 0, {color: BIRD_LEG, width: 5});
    }
    P.group({rotate: peck * 0.5}, () => {
      // 尾：一片朝左后方的深色三角形。
      P.poly([[-52, -58], [-124, -44], [-118, -28], [-50, -40]], {fill: BIRD_TAIL, close: true});
      // 身：一个略斜的椭圆。
      P.ellipse(0, -62, 74, 46, {fill: BIRD_BODY, rotate: -0.04});
      // 翅：深一档的椭圆，加两条横向纹理；扑翅时绕肩部抬起。
      P.group({at: [-6, -70], rotate: -flap * 1.1}, () => {
        P.ellipse(-4, 6, 52, 30, {fill: BIRD_WING, rotate: -0.2});
        P.line(-42, 12, 24, 12, {color: BIRD_WING_LINE, width: 6});
        P.line(-46, 24, 16, 24, {color: BIRD_WING_LINE, width: 5});
      });
      // 颈：两个偏扁的色环，绿在前、紫在后。
      P.ellipse(48, -104, 24, 34, {fill: BIRD_BODY, rotate: 0.28});
      P.ellipse(46, -98, 22, 16, {fill: BIRD_NECK_GREEN, rotate: 0.28});
      P.ellipse(50, -86, 20, 12, {fill: BIRD_NECK_PURPLE, rotate: 0.28});
      // 头、喙、眼：头随点头上下微动。
      const headY = -140 + bob * 7;
      P.circle(62, headY, 24, {fill: BIRD_BODY});
      P.poly([[82, headY - 5], [110, headY + 2], [82, headY + 9]], {fill: BIRD_BEAK, close: true});
      P.circle(70, headY - 7, 7, {fill: '#E8842A'});
      P.circle(70, headY - 7, 3, {fill: '#1E1A1A'});
    });
  });
}

/**
 * 计时器：墙上的实物，一圈 15 秒。
 *
 * 画法是自己的一套——环形刻度 + 走过的扇区 + 一根指针 + 读数，不用参考片的表盘构图。
 * 读数显示剩余秒数，跨幕连续。
 */
function feederTimer(P: P, x: number, y: number, radius: number, globalSeconds: number, alpha = 1, pulse = 0) {
  const phase = ((globalSeconds % FEED_INTERVAL) + FEED_INTERVAL) % FEED_INTERVAL;
  const ratio = phase / FEED_INTERVAL;
  P.group({alpha}, () => {
    // 表壳：一圈深木色边框 + 米白表面。
    P.circle(x, y, radius * 1.1, {fill: '#2B2420'});
    P.circle(x, y, radius, {fill: '#F3EAD6'});
    // 走过的扇区：从顶端顺时针铺到当前时刻。
    const steps = 72;
    const drawn = Math.round(steps * ratio);
    for (let index = 0; index < drawn; index += 1) {
      const from = -Math.PI / 2 + (index / steps) * Math.PI * 2;
      const to = -Math.PI / 2 + ((index + 1) / steps) * Math.PI * 2;
      P.poly([[x, y], [x + Math.cos(from) * radius * 0.94, y + Math.sin(from) * radius * 0.94],
        [x + Math.cos(to) * radius * 0.94, y + Math.sin(to) * radius * 0.94]],
        {fill: TRACK, alpha: 0.26});
    }
    // 15 个刻度，每 5 秒一个粗刻度。
    for (let index = 0; index < FEED_INTERVAL; index += 1) {
      const angle = -Math.PI / 2 + (index / FEED_INTERVAL) * Math.PI * 2;
      const inner = radius * (index % 5 === 0 ? 0.8 : 0.88);
      P.line(x + Math.cos(angle) * inner, y + Math.sin(angle) * inner,
        x + Math.cos(angle) * radius * 0.96, y + Math.sin(angle) * radius * 0.96,
        {color: INK, width: index % 5 === 0 ? radius * 0.045 : radius * 0.022});
    }
    // 指针与轴心。
    const tip = -Math.PI / 2 + ratio * Math.PI * 2;
    P.line(x, y, x + Math.cos(tip) * radius * 0.78, y + Math.sin(tip) * radius * 0.78,
      {color: TRACK, width: radius * 0.07});
    P.circle(x, y, radius * 0.09, {fill: INK});
    // 读数：剩余秒数。字号随半径走，特写与全景都读得清。
    const remain = Math.max(0, Math.ceil(FEED_INTERVAL - phase));
    P.text(String(remain), x, y + radius * 0.44, {size: radius * 0.36, color: INK, font: SANS});
    P.text('秒', x, y + radius * 0.68, {size: radius * 0.18, color: '#8A7554', font: SANS});
    // 画面与声音引用同一幕内事件：滴答事件到达时表盘短暂发亮。
    if (pulse > 0) P.glow(x, y, radius * 2.1, '#FFD27A', 0.4 * pulse);
  });
}

/**
 * 箱子内部：四面木板、米色墙面、木地板，右侧带盖的食槽。
 *
 * `drop` 是这一刻食物落下的进度（0–1）；`stocked` 是盘里还剩多少谷子（0–1，
 * 落下后保持、被吃光才降）。谷子**留在盘里**——它会消失的话，鸽子就吃不到，
 * 「碰巧在转圈」这条因果也就断了。
 */
function boxRoom(P: P, drop: number, stocked: number) {
  // 外框与墙。
  P.rect(0, 0, ROOM_W, ROOM_H, {fill: FRAME_WOOD});
  P.rect(WALL_INSET_X, WALL_TOP, ROOM_W - WALL_INSET_X * 2, WALL_BOTTOM - WALL_TOP, {fill: WALL});
  // 墙板缝：横向的细线，给墙面一个尺度参照。
  for (let index = 1; index < 9; index += 1) {
    const y = WALL_TOP + index * ((WALL_BOTTOM - WALL_TOP) / 9);
    P.line(WALL_INSET_X, y, ROOM_W - WALL_INSET_X, y, {color: WALL_LINE, width: 2, alpha: 0.55});
  }
  // 墙脚的浅色台面与下方的深色地板。
  P.rect(WALL_INSET_X, WALL_BOTTOM - 62, ROOM_W - WALL_INSET_X * 2, 62, {fill: FLOOR});
  P.rect(0, WALL_BOTTOM - 4, ROOM_W, ROOM_H - WALL_BOTTOM + 4, {fill: PLANK});
  // 食槽：墙上开一个投食口，下方是一个斜口盘。
  const [fx, fy] = FEEDER;
  const opening = drop > 0 ? Math.min(1, Math.min(drop * 5, (1 - drop) * 4)) : 0;
  P.rect(fx, fy, 240, 132, {fill: '#4A3A2C', radius: 10});
  P.rect(fx + 12, fy + 12, 216, Math.max(0, 108 * (1 - opening)), {fill: '#8A7250', radius: 8});
  P.poly([[fx - 26, fy + 158], [fx + 266, fy + 158], [fx + 232, fy + 214], [fx + 8, fy + 214]],
    {fill: '#3A2A22', close: true});
  // 谷子：落下过程中一路铺到盘里，落定后按库存留在盘底。
  if (drop <= 0 && stocked <= 0) return;
  const settled = drop > 0 ? smooth(drop) : 1;
  for (let index = 0; index < 14; index += 1) {
    const order = 1 - index / 14;
    const arrive = drop > 0 ? clamp(drop * 2.4 - index * 0.05) : 1;
    if (arrive <= 0) continue;
    // 库存耗尽时从后往前少几颗，视觉上像被吃掉。
    if (stocked < order) continue;
    const gx = fx + 40 + ((index * 41) % 160);
    const settledY = fy + 176 + (index % 3) * 9;
    const gy = drop > 0 ? fy + 70 + smooth(arrive) * (settledY - fy - 70) : settledY;
    P.circle(gx, gy, 8, {fill: GRAIN});
    // 落下时的一点亮，让「食物掉下来」这个动作有分量。
    if (drop > 0 && arrive < 1) P.glow(gx, gy, 26, '#FFD27A', 0.4 * (1 - arrive) * settled);
  }
}

/** 转圈轨迹：绕鸟一圈的虚线椭圆，进度随全片时间推进。 */
function turnTrack(P: P, x: number, y: number, radiusX: number, radiusY: number, progress: number) {
  if (progress <= 0) return;
  const steps = 44;
  const drawn = Math.round(steps * clamp(progress));
  for (let index = 0; index < drawn; index += 1) {
    if (index % 2) continue;
    const from = Math.PI / 2 + (index / steps) * Math.PI * 2;
    const to = Math.PI / 2 + ((index + 1) / steps) * Math.PI * 2;
    P.line(x + Math.cos(from) * radiusX, y + Math.sin(from) * radiusY,
      x + Math.cos(to) * radiusX, y + Math.sin(to) * radiusY,
      {color: TRACK, width: 8, alpha: 0.75});
  }
}

/**
 * 全片时间轴上的喂食状态。
 *
 * 「上一次喂食」取所有不晚于当前时刻的喂食点里最大的那个；`drop` 只在这一刻之后
 * `DROP_SECONDS` 内非零。这样第 15 秒与第 30 秒各掉一次，跨幕不会漏掉。
 *
 * `stocked` 是盘里还剩多少谷子：落下时涨满，随后被吃掉、逐次减少。
 * 两次喂食之间它归零，所以「食物来时才有得吃」这件事在画面上成立。
 */
function feedPhase(globalSeconds: number): {drop: number; stocked: number} {
  const past = FEED_TIMES.filter(at => at <= globalSeconds);
  if (!past.length) return {drop: 0, stocked: 0};
  const last = past[past.length - 1];
  const since = globalSeconds - last;
  const drop = since < DROP_SECONDS ? since / DROP_SECONDS : 0;
  // 落定后才算有货；隔一次喂食的间隔里慢慢被吃光。
  const eatFrom = DROP_SECONDS;
  const eatSpan = FEED_INTERVAL - DROP_SECONDS - 1.5;
  const stocked = drop > 0 ? 0 : clamp(1 - (since - eatFrom) / eatSpan);
  return {drop, stocked};
}

/**
 * 一条全片状态轨迹：找吃的 → 碰巧转圈 → 跑到食槽吃 → 又转、再转。
 *
 * 位置、朝向、啄食、步态与转圈轨迹全部由全片秒数决定，不读取幕 ID；六幕只是
 * 同一房间的六段取景。这样换镜时读到的仍是同一条轨迹，不会因为换幕跳到另一套动作。
 */
const HOME = 980;
const FEED_SPOT = 1360;

/** 按全片时间在关键点之间做平滑插值；首尾之外保持端值。 */
function track(t: number, points: Array<[number, number]>): number {
  let index = 0;
  while (index < points.length - 2 && t >= points[index + 1][0]) index += 1;
  const [fromTime, fromValue] = points[index];
  const [toTime, toValue] = points[index + 1];
  return fromValue + (toValue - fromValue) * smooth((t - fromTime) / Math.max(1e-6, toTime - fromTime));
}

/** 一个啄食窗口；两端都平滑回到 0，避免窗口边界突然抬头。 */
function peckAt(t: number, start: number, end: number): number {
  if (t <= start || t >= end) return 0;
  const envelope = Math.max(0, Math.min(1, (t - start) * 6, (end - t) * 6));
  return Math.max(0, Math.sin((t - start) * 9)) * 0.8 * envelope;
}

/** 事件到达后的短暂视觉强调；画面与音效读取同一份幕内事件帧。 */
function eventPulse(events: ReturnType<typeof createSceneEvents>, ids: string[], frame: number,
  spanFrames = 6): number {
  let value = 0;
  for (const id of ids) {
    try {
      const at = events.frame(id);
      if (frame >= at && frame < at + spanFrames) value = Math.max(value, 1 - (frame - at) / spanFrames);
    } catch {
      // 当前幕没有声明该事件时不强调，不影响画面。
    }
  }
  return value;
}

function act(t: number) {
  const x = track(t, [
    [0, HOME], [4, HOME], [8, 1040], [9, 1040],
    [10.3, 860], [11.6, 860], [13.2, 1000], [15.2, 1000],
    [16.0, FEED_SPOT], [19.0, FEED_SPOT], [19.9, 860], [26.5, 860],
    [30.2, 860], [30.9, FEED_SPOT], [33, FEED_SPOT],
  ]);
  const turn = track(t, [
    [0, 0], [9, 0], [11.5, 0], [11.9, Math.PI], [13.4, Math.PI],
    [15.0, 3 * Math.PI], [15.3, 4 * Math.PI], [19.0, 4 * Math.PI],
    [19.3, 5 * Math.PI], [20.2, 5 * Math.PI], [22.2, 7 * Math.PI],
    [23.6, 7 * Math.PI], [25.6, 9 * Math.PI], [26.4, 9 * Math.PI],
    [28.0, 11 * Math.PI], [28.4, 11 * Math.PI], [29.9, 13 * Math.PI],
    [30.2, 14 * Math.PI], [33, 14 * Math.PI],
  ]);
  const peck = Math.min(0.9,
    peckAt(t, 4.8, 6.0) + peckAt(t, 6.8, 8.0) + peckAt(t, 10.4, 11.5)
    + peckAt(t, 16.2, 18.9) + peckAt(t, 31.1, 32.6));
  const moving = (t > 4.2 && t < 4.8) || (t > 6.2 && t < 6.8) || (t > 9 && t < 10.3)
    || (t > 11.9 && t < 13.2) || (t > 15.2 && t < 16) || (t > 19 && t < 19.9)
    || (t > 30.2 && t < 30.9);
  // 第一次是「碰巧」的转圈，第二次是重复动作；轨迹画在同一条地面上。
  const trail = Math.max(
    smooth((t - 13.5) / 0.4) * (1 - smooth((t - 15.0) / 0.3)),
    smooth((t - 20.2) / 0.4) * (1 - smooth((t - 29.9) / 0.3)),
  );
  return {
    x,
    turn,
    facing: Math.cos(turn) >= 0 ? 1 : -1,
    peck,
    flap: 0,
    bob: moving ? Math.sin(t * 12) * 0.5 + 0.5 : 0.5,
    trail: clamp(trail),
  };
}

// ---------------------------------------------------------------- 场景

export default function Pigeon(props: CodeSceneProps & Props) {
  const {width, height, fps, subtitleSafeArea, props: values, durationInFrames} = props;
  const {chapter, gauge, screenSubtitles} = values;
  const {elapsedSeconds, globalSeconds, ready} = useSceneContext();
  const frame = Math.round(elapsedSeconds * fps);
  const {drop, stocked} = feedPhase(globalSeconds);
  const inside = chapter.id !== 'box';
  const state = act(globalSeconds);
  const shot = shotAt(chapter.id, elapsedSeconds / Math.max(0.001, durationInFrames / fps));
  const events = createSceneEvents(props.eventFrames);
  const tickIds = chapter.id === 'feeder'
    ? ['tick-1', 'tick-2', 'tick-3', 'tick-4', 'tick-5']
    : chapter.id === 'again' ? ['tick-fast-1', 'tick-fast-2', 'tick-fast-3'] : [];
  const tickPulse = eventPulse(events, tickIds, frame);
  const feedPulse = eventPulse(events, ['feed-1-arrival', 'feed-2-arrival'], frame, 10);

  useEffect(() => {
    let active = true;
    document.fonts.ready.then(() => {if (active) ready();});
    return () => {active = false;};
  }, [ready]);

  const at = (): Vec => [width / 2 - shot.focus[0] * shot.scale, height / 2 - shot.focus[1] * shot.scale];

  return (
    <div style={{position: 'absolute', inset: 0, width, height}}>
      <FableStage scene={inside ? 'desk' : 'night'} width={width} height={height} horizon={0.74}/>
      <painter.PainterCanvas width={width} height={height} bloom={0.1} grain={0.05} seed={chapter.id.length + 5}
        paint={(P) => {
          // 透明底：房间自己铺满，下面的 FableStage 只在箱子外的镜头里露出来。
          P.clear('rgba(0,0,0,0)');
          if (!inside) {
            // 箱子外的全景：桌上的木箱、头顶的灯、箱里一只点头的鸽子。
            P.rect(0, 0, width, height, {fill: '#241F28'});
            const bx = width * 0.08;
            const by = height * 0.13;
            const bw = width * 0.58;
            const bh = height * 0.62;
            P.rect(bx - 16, by - 16, bw + 32, bh + 32, {fill: FRAME_WOOD});
            P.rect(bx, by, bw, bh, {fill: WALL});
            P.rect(bx, by + bh - 62, bw, 62, {fill: FLOOR});
            // 灯：一束锥形的暖光。
            P.path(`M ${bx + bw / 2 - 46},${by - 128} L ${bx + bw / 2 + 46},${by - 128} `
              + `L ${bx + bw / 2 + 208},${by + bh} L ${bx + bw / 2 - 208},${by + bh} Z`,
              {fill: '#FFE7B0', alpha: 0.05});
            P.ellipse(bx + bw / 2, by - 134, 34, 10, {fill: '#FFE7B0', alpha: 0.5});
            bird(P, bx + bw * 0.42, by + bh - 78, 0.8, {
              peck: Math.sin(globalSeconds * 2.4) > 0.4 ? 0.7 : 0.1,
              bob: Math.sin(globalSeconds * 2.9) * 0.4,
            });
            feederTimer(P, width * 0.84, height * 0.33, 86, globalSeconds, 0.95);
            return;
          }
          // 箱内：房间整体按镜头取景缩放与平移。
          P.group({at: at(), scale: shot.scale}, () => {
            boxRoom(P, drop, stocked);
            if (feedPulse > 0) P.glow(FEEDER[0] + 120, FEEDER[1] + 180, 180, '#FFD27A', 0.45 * feedPulse);
            feederTimer(P, TIMER[0], TIMER[1], TIMER_R, globalSeconds, 1, tickPulse);
            if (state.trail > 0) {
              turnTrack(P, HOME, FLOOR_Y - 58, 230, 52, state.trail);
            }
            bird(P, state.x, FLOOR_Y - 62, 1.5, {
              facing: state.facing, turn: state.turn, peck: state.peck, flap: state.flap, bob: state.bob,
            });
          });
        }}
        post={(P) => {
          // 暖色暗角：压住四角，把视线收在食槽与鸽子之间。画在辉光之后，
          // 否则会被内容层的亮色冲淡。
          const vignette = P.radialGradient(width / 2, height * 0.5, width * 0.3,
            width / 2, height * 0.5, width * 0.76,
            [[0, '#3A2410', 0], [0.72, '#3A2410', 0.16], [1, '#3A2410', 0.55]]);
          P.rect(0, 0, width, height, {fill: vignette});
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
