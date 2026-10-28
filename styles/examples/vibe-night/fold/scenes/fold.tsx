/**
 * 《折叠》示例：一串珠子怎么折，决定细胞是什么形状。
 *
 * 选题与分镜按外部参考项目已登记的 fold_C 样片重写；实现、形状与配色来自本仓库的
 * `vibe-night` 组件与绘制原语，不复制上游 `film.js`、GIF/JPG 或画面。
 *
 * 九幕共用一套逻辑坐标：血管 → 红细胞 → 血红蛋白链 → 珠子 → 折叠 → 长杆 → 镰刀。
 * 每幕只让观众明白一个关系；「提问」与「收尾」两幕基本静止。
 */
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps, painter} from 'm2v/code-scene';
import NightBackdrop from 'm2v/style/components/night-backdrop';
import GlowText from 'm2v/style/components/glow-text';
import ChapterMark from 'm2v/style/components/chapter-mark';
import Dip from 'm2v/style/components/dip';
import NumberLine from 'm2v/style/components/number-line';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
import {loadNightSerif} from 'm2v/style/components/kit';

type Chapter = {id: string; index: string; character: string; title: string; caption: string};
type Subtitle = {startFrame: number; endFrame: number; text: string};
type Props = {chapter: Chapter; screenSubtitles: Subtitle[]; credit?: string};

const WHITE = '#F8F9F8';
const GOLD = '#F8D893';
const ICE = '#64E3F6';
const ROSE = '#E84B75';
const VIOLET = '#8477D0';
// 画布文字使用包内登记的宋体族；`serif` 是通用族，会静默回退到系统字体。
const SERIF = '"Vibe Night Serif", "Noto Serif SC", serif';

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {const t = clamp(value); return t * t * (3 - 2 * t);};
const mix = (index: number, total: number) => total <= 1 ? 0 : index / (total - 1);

/** 珠子：一颗带高光与阴影的球，冰蓝是正常，玫红是错的那颗。 */
function bead(P: InstanceType<typeof painter.Painter>, x: number, y: number, radius: number,
              tint: string, alpha = 1) {
  P.group({alpha}, () => {
    P.circle(x, y, radius, {fill: tint, alpha: 0.92});
    P.group({alpha: 0.5}, () => P.circle(x - radius * 0.3, y - radius * 0.32, radius * 0.42,
      {fill: '#FFFFFF', alpha: 0.55}));
    P.circle(x + radius * 0.28, y + radius * 0.3, radius * 0.55, {fill: '#000000', alpha: 0.12});
  });
  P.glow(x, y, radius * 2.1, tint, 0.28 * alpha);
}

/** 红细胞：双凹圆盘，画成两段弧围出的扁圆。 */
function cell(P: InstanceType<typeof painter.Painter>, x: number, y: number, radius: number,
              squash: number, alpha = 1, tint = '#CFEAF4') {
  P.group({alpha}, () => {
    P.ellipse(x, y, radius, radius * squash, {fill: tint, alpha: 0.9});
    // 双凹：中间一圈更暗的凹陷，只压到 0.35，避免整体发灰
    P.ellipse(x, y, radius * 0.52, radius * squash * 0.4, {fill: '#1B2A44', alpha: 0.35});
    P.ellipse(x - radius * 0.28, y - radius * squash * 0.45, radius * 0.42, radius * squash * 0.14,
      {fill: '#FFFFFF', alpha: 0.3});
  });
  P.glow(x, y, radius * 1.7, tint, 0.16 * alpha);
}

/**
 * 镰刀形：由「圆盘」连续弯成的一把镰刀，而不是圆盘里嵌一条弧。
 *
 * 画法是一串沿弧线排布的实心圆：`bend = 0` 时弧线绕成整圈、圆足够粗，拼成一个圆盘；
 * `bend = 1` 时弧线收到 205°，圆在中段最粗、两端收成尖，拼成一把镰刀。
 * 相邻圆的间距远小于半径，因此轮廓连续；用实心圆而不是自交多边形，填充不会出错。
 */
/**
 * 镰刀形：由「圆盘」连续弯成一把镰刀。
 *
 * 沿一条弧线排布一串实心圆：`bend = 0` 时弧线绕成整圈、圆足够粗，拼成圆盘；
 * 弯下时弧线收短、圆在中段最粗、两端收尖，拼成一把月牙形的镰刀。
 * 相邻圆心距始终小于半径（约 1.4 px 对数十 px），轮廓连续；用实心圆而不是
 * 自交多边形，填充不会出错，也不依赖外部路径。
 */
function sickleShape(P: InstanceType<typeof painter.Painter>, x: number, y: number, size: number,
                     bend: number, alpha = 1, tint = '#D8AEBE') {
  const amount = clamp(bend);
  const samples = 150;
  // 弯下后外径会缩小；按比例补偿，让镰刀与圆盘保持同一屏幕尺度。
  const scale = size * (1 + 0.34 * amount);
  const span = (Math.PI / 180) * (360 * (1 - amount) + 200 * amount);
  const centreRadius = scale * (0.3 + 0.32 * amount);
  const halfWidth0 = scale * (0.74 - 0.62 * amount);
  const startAngle = -Math.PI / 2 - span / 2 + (Math.PI / 180) * 55 * amount;
  const squash = 0.9;
  P.group({alpha}, () => {
    for (let index = 0; index < samples; index += 1) {
      const t = index / (samples - 1);
      const taper = Math.pow(Math.sin(Math.PI * t), 0.8);
      const halfWidth = halfWidth0 * ((1 - amount) + amount * taper);
      if (halfWidth <= 0.5) continue;
      const angle = startAngle + span * t;
      P.circle(x + Math.cos(angle) * centreRadius, y + Math.sin(angle) * centreRadius * squash,
        halfWidth, {fill: tint, alpha: 0.94});
    }
    // 圆盘时的双凹随弯下消失；弯下后沿外缘点一道更亮的刃口
    if (amount < 0.5) {
      P.ellipse(x, y, size * 0.5, size * 0.34, {fill: '#1B2A44', alpha: 0.3 * (1 - amount * 2)});
    } else {
      for (let index = 12; index < samples - 12; index += 5) {
        const t = index / (samples - 1);
        const taper = Math.pow(Math.sin(Math.PI * t), 0.8);
        const halfWidth = halfWidth0 * ((1 - amount) + amount * taper);
        const angle = startAngle + span * t;
        P.circle(x + Math.cos(angle) * centreRadius, y + Math.sin(angle) * centreRadius * squash,
          Math.max(0.6, halfWidth * 0.14), {fill: '#FFFFFF', alpha: 0.18 * amount});
      }
    }
  });
  P.glow(x, y, size * 1.4, tint, 0.14 * alpha);
}

/** 珠串位置：沿一条缓慢起伏的曲线排开，位置只由序号与固定种子决定。 */
function chainPoints(count: number, width: number, y: number, spread: number): painter.Point[] {
  return Array.from({length: count}, (_, index) => {
    const t = mix(index, count);
    return [width / 2 + (t - 0.5) * spread, y + Math.sin(t * Math.PI * 2.2) * 16];
  });
}

function ChainScene({frame, width, height, reveal}: {frame: number; width: number; height: number; reveal: number}) {
  const points = chainPoints(146, width, height * 0.5, width * 0.66);
  const lit = Math.round(146 * smooth(reveal));
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={11}
    paint={(P) => {
      P.clear('#010104');
      points.forEach((point, index) => {
        if (index >= Math.max(1, lit)) return;
        const radius = 5.4;
        bead(P, point[0], point[1], radius, index === 0 ? GOLD : ICE, 1);
      });
      // 数到 146 的进度：一条随珠子亮起生长的细线
      const end = points[Math.max(0, Math.min(points.length - 1, lit - 1))];
      const start = points[0];
      P.line(start[0], start[1] + 46, end[0], end[1] + 46, {color: '#879399', width: 1.1, alpha: 0.55});
    }}/>;
}

function MutationScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const points = chainPoints(12, width, height * 0.52, width * 0.56);
  const flip = smooth((frame - 46) / 34);
  const letters = ['V', 'H', 'L', 'T', 'P', 'E', 'E', 'K', 'S', 'A', 'V', 'T'];
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={12}
    paint={(P) => {
      P.clear('#010104');
      points.forEach((point, index) => {
        bead(P, point[0], point[1], 17, index === 5 ? ROSE : ICE, 1);
      });
      // 第 6 颗字母翻转：E → V
      const sixth = points[5];
      const shown = flip < 0.5 ? 'E' : 'V';
      P.text(shown, sixth[0], sixth[1] - 46, {
        size: 30, color: flip > 0.1 ? ROSE : '#879399', font: SERIF, role: 'letter-sixth',
        state: shown === 'V' ? 'mutated' : 'normal',
      });
      points.forEach((point, index) => {
        if (index === 5) return;
        P.text(letters[index], point[0], point[1] - 46, {size: 24, color: '#879399', font: SERIF, alpha: 0.75});
      });
      P.text('第 6 位：谷氨酸 E → 缬氨酸 V', width / 2, height * 0.78, {
        size: 30, color: flip > 0.5 ? GOLD : '#879399', font: SERIF,
      });
    }}/>;
}

function SickleScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const bend = smooth((frame - 34) / 58);
  const radius = 168;
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={13}
    paint={(P) => {
      P.clear('#010104');
      // 左边保持圆细胞作对照，右边同一个形状连续弯成镰刀
      cell(P, width * 0.27, height * 0.48, radius, 1, 0.5);
      sickleShape(P, width * 0.66, height * 0.48, radius, bend, 1, bend > 0.5 ? '#D8AEBE' : '#CFEAF4');
      P.text('红细胞', width * 0.27, height * 0.8, {size: 30, color: '#879399', font: SERIF});
      P.text(bend > 0.6 ? '镰状细胞' : '红细胞', width * 0.66, height * 0.8, {
        size: 30, color: bend > 0.6 ? ROSE : '#879399', font: SERIF, role: 'cell-label',
        state: bend > 0.6 ? 'sickle' : 'round',
      });
    }}/>;
}

function QuestionScene({width, height}: {width: number; height: number}) {
  return <painter.PainterCanvas width={width} height={height} bloom={0.7} grain={0.05} seed={14}
    paint={(P) => {
      P.clear('#010104');
      sickleShape(P, width / 2, height * 0.46, 200, 1, 0.72, '#C09AAE');
    }}/>;
}

function FoldScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const fold = smooth((frame - 18) / 76);
  const oxygen = smooth((frame - 74) / 30);
  const points = chainPoints(146, width, height * 0.5, width * 0.62);
  // 折叠目标：把珠串卷成一个球，中间留一个小窝
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={15}
    paint={(P) => {
      P.clear('#010104');
      const cx = width / 2;
      const cy = height * 0.48;
      points.forEach((point, index) => {
        const t = mix(index, points.length);
        const angle = t * Math.PI * 2 * 3.2;
        const ringRadius = 118 + Math.sin(t * 9) * 16;
        const targetX = cx + Math.cos(angle) * ringRadius * (1 + 0.22 * Math.cos(t * 5));
        const targetY = cy + Math.sin(angle) * ringRadius * (0.86 + 0.2 * Math.sin(t * 7));
        const x = point[0] + (targetX - point[0]) * fold;
        const y = point[1] + (targetY - point[1]) * fold;
        bead(P, x, y, 5.4, index === 0 ? GOLD : ICE, 1);
      });
      if (oxygen > 0) {
        // 一个氧分子飞进球中间的窝，落下时亮一下
        const ox = cx + (1 - oxygen) * 300;
        const oy = cy - 40 - Math.sin(oxygen * Math.PI) * 90;
        P.circle(ox, oy, 13, {fill: '#94FDFF', alpha: 0.85 * oxygen});
        P.glow(ox, oy, 54, '#94FDFF', 0.55 * oxygen);
        P.text('O₂', ox + 34, oy, {size: 26, color: ICE, font: SERIF, alpha: oxygen, role: 'oxygen'});
      }
    }}/>;
}

function StickyScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const glow = 0.55 + 0.45 * Math.sin(frame * 0.14);
  const cx = width / 2;
  const cy = height * 0.47;
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={16}
    paint={(P) => {
      P.clear('#010104');
      for (let index = 0; index < 146; index += 1) {
        const t = mix(index, 146);
        const angle = t * Math.PI * 2 * 3.2;
        const ringRadius = 118 + Math.sin(t * 9) * 16;
        const x = cx + Math.cos(angle) * ringRadius * (1 + 0.22 * Math.cos(t * 5));
        const y = cy + Math.sin(angle) * ringRadius * (0.86 + 0.2 * Math.sin(t * 7));
        bead(P, x, y, 5.4, ICE, 0.9);
      }
      // 表面鼓出的玫红珠子：黏点
      const sx = cx + 120;
      const sy = cy - 16;
      bead(P, sx, sy, 13 + 3 * glow, ROSE, 1);
      P.glow(sx, sy, 60 * glow, ROSE, 0.5 * glow);
      P.text('放下氧气以后 · 黏点', width / 2, height * 0.8, {size: 30, color: ROSE, font: SERIF});
    }}/>;
}

function RodScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const built = Math.floor(1 + 8 * smooth((frame - 14) / 62));
  const cx = width / 2;
  const cy = height * 0.48;
  return <painter.PainterCanvas width={width} height={height} bloom={0.9} grain={0.05} seed={17}
    paint={(P) => {
      P.clear('#010104');
      for (let index = 0; index < built; index += 1) {
        const x = cx - 400 + index * 96;
        bead(P, x, cy, 15, ICE, 0.9);
        if (index > 0) {
          bead(P, x - 48, cy, 10, ROSE, 0.95);
        }
      }
      P.text('一个粘一个', width / 2, height * 0.78, {size: 30, color: '#879399', font: SERIF});
    }}/>;
}

function PushScene({frame, width, height}: {frame: number; width: number; height: number}) {
  const bend = smooth((frame - 18) / 46);
  const cx = width / 2;
  const cy = height * 0.44;
  return <painter.PainterCanvas width={width} height={height} bloom={0.28} grain={0.05} seed={18}
    paint={(P) => {
      P.clear('#010104');
      // 细胞本身被从里面顶弯：同一形状连续变形，长杆压在细胞轮廓之内
      sickleShape(P, cx, cy, 230, bend, 0.85, bend > 0.45 ? '#B87F92' : '#5A7F99');
      // 长杆随弯曲增多、变长
      for (let index = 0; index < 8; index += 1) {
        const t = mix(index, 8);
        const length = (90 + 300 * bend) * (0.35 + 0.65 * Math.sin(t * Math.PI));
        P.line(cx - length / 2, cy - 80 + t * 160, cx + length / 2, cy - 80 + t * 160,
          {color: ROSE, width: 3.4, alpha: 0.4 + 0.55 * bend});
      }
    }}/>;
}

function ClosingScene({width, height}: {width: number; height: number}) {
  return <painter.PainterCanvas width={width} height={height} bloom={0.8} grain={0.06} seed={19}
    paint={(P) => {
      P.clear('#010104');
      // 镰刀上移，给下方的结论句留出位置
      sickleShape(P, width / 2, height * 0.36, 150, 1, 0.72, '#C09AAE');
    }}/>;
}

export default function Fold(props: CodeSceneProps & Props) {
  const {width, height, fps, subtitleSafeArea, props: values} = props;
  const {chapter, screenSubtitles, credit} = values;
  const {elapsedSeconds, ready} = useSceneContext();
  useEffect(() => { loadNightSerif().then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  const total = props.durationInFrames;
  const chapterStart = Math.round(total * 0.16);

  const scene = (() => {
    switch (chapter.id) {
      case 'chain': return <ChainScene frame={frame} width={width} height={height} reveal={(frame - 12) / 90}/>;
      case 'mutation': return <MutationScene frame={frame} width={width} height={height}/>;
      case 'sickle': return <SickleScene frame={frame} width={width} height={height}/>;
      case 'question': return <QuestionScene width={width} height={height}/>;
      case 'fold': return <FoldScene frame={frame} width={width} height={height}/>;
      case 'sticky': return <StickyScene frame={frame} width={width} height={height}/>;
      case 'rod': return <RodScene frame={frame} width={width} height={height}/>;
      case 'push': return <PushScene frame={frame} width={width} height={height}/>;
      default: return <ClosingScene width={width} height={height}/>;
    }
  })();

  return (
    <div style={{position: 'absolute', inset: 0, width, height}}>
      <NightBackdrop width={width} height={height} frame={frame} seed={chapter.id}/>
      {scene}
      {chapter.id !== 'closing' ? (
        <ChapterMark index={chapter.index} character={chapter.character} frame={frame} startFrame={chapterStart}/>
      ) : null}
      <GlowText text={chapter.title} x={width / 2} y={chapter.id === 'closing' ? 860 : 96}
        size={chapter.id === 'closing' ? 52 : 40} color={chapter.id === 'closing' ? GOLD : WHITE}
        glow={chapter.id === 'closing' ? 0.7 : 0.35}/>
      {chapter.id === 'chain' ? (
        <NumberLine x={width * 0.18} y={height * 0.78} width={width * 0.64} min={0} max={146}
          ticks={3} labels={['0', '73', '146']} marker={146} markerLabel="146 颗"
          frame={frame} startFrame={12} revealFrames={80}/>
      ) : null}
      {credit ? (
        <GlowText text={credit} x={width / 2} y={940} size={26} color="#8A97A5" glow={0.2}/>
      ) : null}
      <ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={subtitleSafeArea} fps={fps}/>
      <Dip frame={frame} startFrame={0} durationFrames={14} peak={0.9}/>
      <Dip frame={frame} startFrame={total - 14} durationFrames={14} peak={0.9} holdEnd/>
    </div>
  );
}
