import {useCallback, useMemo, useRef} from 'react';
import {type CodeSceneProps, type Look, type Shot} from 'm2v/code-scene';
import {BODIES, CHAPTER_IDS, CHAPTERS} from './bodies';
import {useNarration} from './clock';
import {useTextures, useTextureSources} from './world';
import {SolarSystem} from './solar-system';

/** 压缩坐标 → 天文单位的锚点：按天体真实平均日距标定，中间线性插值，仅作读数示意。 */
const AU_ANCHORS: [number, number][] = [
  [0, 0], [8, 0.39], [12, 0.72], [17, 1], [23, 1.52], [29, 2.77], [38, 5.2], [51, 9.58],
  [66, 19.2], [80, 30.1], [94, 39.5], [132, 120], [185, 2000], [245, 100000],
];

export function auAt(radius: number): number {
  if (radius <= 0) return 0;
  for (let index = 0; index < AU_ANCHORS.length - 1; index += 1) {
    const [lowRadius, lowAu] = AU_ANCHORS[index];
    const [highRadius, highAu] = AU_ANCHORS[index + 1];
    if (radius <= highRadius) {
      const t = (radius - lowRadius) / (highRadius - lowRadius);
      // 外太阳系跨度太大，用对数插值才不会把 2000 AU 压成一条直线。
      const value = lowAu <= 0 ? lowAu + (highAu - lowAu) * t
        : Math.exp(Math.log(lowAu) + (Math.log(highAu) - Math.log(lowAu)) * t);
      return value;
    }
  }
  return AU_ANCHORS[AU_ANCHORS.length - 1][1];
}

export function formatAu(value: number): string {
  if (value < 0.1) return value.toFixed(3);
  if (value < 10) return value.toFixed(2);
  if (value < 1000) return Math.round(value).toString();
  return `${(value / 1000).toFixed(1)} 千`;
}

/** 当前帧落在哪个镜头里；与 SDK 的 activeShot 同一口径（endFrame 为开区间）。 */
export function shotAt(shots: Shot[], frame: number): Shot | null {
  for (const shot of shots) {
    if (frame >= shot.startFrame && frame < shot.endFrame) return shot;
  }
  return null;
}

/** 按镜头路径插值出当前半径，用于 AU 读数；不复制相机的缓动实现，只取几何量。 */
export function pathRadiusAt(shot: Shot | null, progress: number): number {
  const points = shot?.camera?.path;
  if (!points || points.length === 0) return 0;
  const t = Math.min(1, Math.max(0, progress)) * (points.length - 1);
  const index = Math.min(points.length - 2, Math.floor(t));
  const local = points.length === 1 ? 0 : t - index;
  const first = points[index];
  const second = points[Math.min(points.length - 1, index + 1)];
  const radius = (point: number[]) => Math.hypot(point[0], point[2]);
  return radius(first) + (radius(second) - radius(first)) * local;
}

/** 镜头内的淡入淡出：0.5 秒斜坡，由帧号算出（CSS 过渡会被录制时钟冻结，不能用）。 */
export function shotFade(shot: Shot | null, frame: number, ramp = 30): number {
  if (!shot) return 0;
  const rise = Math.min(1, Math.max(0, (frame - shot.startFrame) / ramp));
  const fall = Math.min(1, Math.max(0, (shot.endFrame - frame) / ramp));
  return Math.min(rise, fall);
}

export default function Journey(config: CodeSceneProps) {
  const clock = useNarration(config);
  const shots = (config.props.shots ?? []) as Shot[];
  const look = (config.props.look ?? {profile: 'deep-space-cinematic'}) as Look;
  const frame = Math.round(clock.elapsedSeconds * config.fps);
  const shot = useMemo(() => shotAt(shots, frame), [shots, frame]);
  const progress = shot ? (frame - shot.startFrame) / Math.max(1, shot.endFrame - shot.startFrame) : 0;
  const active = shot?.target && BODIES[shot.target] ? shot.target : 'sun';
  const body = BODIES[active];
  const seconds = clock.elapsedSeconds;
  const sources = useTextureSources();
  const textures = useTextures(sources);
  const ready = useRef(clock.ready);
  ready.current = clock.ready;
  const onReady = useCallback(() => ready.current(), []);
  const chapter = Object.keys(config.segmentWindows)[clock.index]?.split('-')[0] ?? 'sun';
  const chapterIndex = Math.max(0, CHAPTER_IDS.indexOf(chapter));
  const au = auAt(pathRadiusAt(shot, progress));
  const opening = shot?.id === 'cold-open';
  const closing = shot?.id === 'oort-hold';
  const fade = shotFade(shot, frame);
  const panel = (!opening && !closing) ? fade : 0;
  const safe = config.subtitleSafeArea;
  const track = (chapterIndex + Math.min(1, Math.max(0, progress))) / CHAPTERS.length;

  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: '#02050a', color: '#f2eee5'}}>
    <div style={{position: 'absolute', inset: 0, zIndex: 0}}>
      {textures && <SolarSystem textures={textures} shots={shots} look={look} active={active}
        seconds={seconds} onReady={onReady}/>}
    </div>
    {/* 字幕 scrim：只在字幕带上下做渐变，不压暗整幅画面。 */}
    <div style={{position: 'absolute', left: 0, right: 0, top: safe.y - 90, height: safe.height + 150,
      pointerEvents: 'none', background: 'linear-gradient(180deg, transparent, rgba(2,5,10,0.82) 45%, rgba(2,5,10,0.92))'}}/>
    <div style={{position: 'absolute', left: 70, right: 70, top: 42, display: 'flex',
      justifyContent: 'space-between', fontSize: 19, letterSpacing: '0.12em', color: '#bdc9d2'}}>
      <span>SOLAR SYSTEM / 太阳系之旅</span>
      <span>{opening ? '冷开场 · 日面边缘' : closing ? '奥尔特云 · 太阳成为亮点' : `正在经过 · ${body.name}`}</span>
    </div>
    {/* 章节进度轨：一条轨加九个刻度，替代常驻左栏。 */}
    <div style={{position: 'absolute', left: 70, right: 70, top: 96}}>
      <div style={{position: 'relative', height: 2, background: 'rgba(132,150,168,0.35)'}}>
        <div style={{position: 'absolute', left: 0, top: 0, height: 2, width: `${track * 100}%`,
          background: 'linear-gradient(90deg, #9c8159, #e7cca2)'}}/>
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 10}}>
        {CHAPTERS.map((name, index) => <span key={name} style={{fontSize: 15,
          color: index === chapterIndex ? '#e7cca2' : index < chapterIndex ? '#9aa9b8' : '#6b7b8a'}}>{name}</span>)}
      </div>
    </div>
    <div style={{position: 'absolute', left: 70, top: 420, width: 460, padding: '26px 28px',
      borderLeft: '1px solid #9c8159', background: 'linear-gradient(90deg, rgba(2,5,10,0.96), rgba(2,5,10,0.72))',
      opacity: panel}}>
      <div style={{fontSize: 17, letterSpacing: '0.18em', color: '#dabb86'}}>{body.english}</div>
      <div style={{fontSize: 64, fontWeight: 350, lineHeight: 1.3, marginTop: 12}}>{body.name}</div>
      <div style={{fontSize: 22, color: '#dabb86', marginTop: 14}}>{body.kind}</div>
      <div style={{fontSize: 23, lineHeight: 1.6, marginTop: 25}}>{body.feature}</div>
      <div style={{fontSize: 19, color: '#a7b5c2', marginTop: 20}}>{body.distance}</div>
    </div>
    <div style={{position: 'absolute', left: 70, bottom: 150, fontSize: 19, color: '#cfe0f2',
      letterSpacing: '0.06em'}}>距太阳 ≈ {formatAu(au)} AU（压缩坐标）</div>
    <div style={{position: 'absolute', left: 70, right: 70, top: safe.y - 60, display: 'flex',
      justifyContent: 'space-between', fontSize: 16, color: '#a3b2c0',
      opacity: opening || closing ? fade : 0}}>
      <span>同一三维模型 · 轨道距离压缩 · 天体放大 · 非实时位置 · 艺术示意</span>
      <span>NASA / JPL / USGS · Solar System Scope（CC BY 4.0）</span>
    </div>
  </div>;
}
