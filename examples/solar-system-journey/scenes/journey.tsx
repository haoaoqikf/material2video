import {useCallback, useMemo, useRef} from 'react';
import {type CodeSceneProps, type Look, type Shot} from 'm2v/code-scene';
import {BODIES, CHAPTER_IDS, CHAPTERS} from './bodies';
import {useNarration} from './clock';
import {useTextures, useTextureSources} from './world';
import {SolarSystem} from './solar-system';

/** 当前帧落在哪个镜头里；与 SDK 的 activeShot 同一口径（endFrame 为开区间）。 */
export function shotAt(shots: Shot[], frame: number): Shot | null {
  for (const shot of shots) {
    if (frame >= shot.startFrame && frame < shot.endFrame) return shot;
  }
  return null;
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
  // 每个对象独立一幕，身份来自本幕语义配置，不依赖旧全片帧号。
  const active = String(config.props.body ?? shot?.target ?? 'sun');
  const body = BODIES[active];
  const seconds = clock.elapsedSeconds;
  const sources = useTextureSources();
  const textures = useTextures(sources);
  const ready = useRef(clock.ready);
  ready.current = clock.ready;
  const onReady = useCallback(() => ready.current(), []);
  const chapter = String(config.props.chapter ?? 'sun');
  const chapterIndex = Math.max(0, CHAPTER_IDS.indexOf(chapter));
  const opening = active === 'sun' && frame < (Object.values(config.segmentWindows)[0]?.startFrame ?? 0);
  const closing = active === 'oort';
  const fade = shotFade(shot, frame);
  const panel = (!opening && !closing && !config.props.hideBodyPanel) ? fade : 0;
  const safe = config.subtitleSafeArea;
  const track = Math.min(1, (Number(config.props.journeyOffsetFrames ?? 0) + frame) / Number(config.props.journeyDurationFrames ?? config.durationInFrames));

  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: '#02050a', color: '#f2eee5'}}>
    <div style={{position: 'absolute', inset: 0, zIndex: 0}}>
      {textures && <SolarSystem textures={textures} shots={shots} look={look} active={active}
        seconds={seconds} fps={config.fps} onReady={onReady}/>}
    </div>
    {/* 顶部 scrim：亮天体经过标题/章节导航后方时仍要保持文字对比度。 */}
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 168,
      pointerEvents: 'none', background: 'linear-gradient(180deg, rgba(2,5,10,0.94) 0%, rgba(2,5,10,0.72) 62%, rgba(2,5,10,0) 100%)'}}/>
    {/* 字幕 scrim：只在字幕带上下做渐变，不压暗整幅画面。 */}
    <div style={{position: 'absolute', left: 0, right: 0, top: safe.y - 90, height: safe.height + 150,
      pointerEvents: 'none', background: 'linear-gradient(180deg, transparent, rgba(2,5,10,0.82) 45%, rgba(2,5,10,0.92))'}}/>
    <div style={{position: 'absolute', left: 70, right: 70, top: 42, display: 'flex',
      justifyContent: 'space-between', fontSize: 26, letterSpacing: '0.12em', color: '#bdc9d2'}}>
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
        {CHAPTERS.map((name, index) => <span key={name} style={{fontSize: 22,
          color: index === chapterIndex ? '#e7cca2' : index < chapterIndex ? '#9aa9b8' : '#6b7b8a'}}>{name}</span>)}
      </div>
    </div>
    <div style={{position: 'absolute', left: 70, top: 390, width: 590, padding: '26px 28px',
      borderLeft: '1px solid #9c8159',
      // 右侧渐隐到透明：半透明底板在亮天体前会露出一条硬直边，像多出一个矩形。
      background: 'linear-gradient(90deg, rgba(2,5,10,0.95) 0%, rgba(2,5,10,0.84) 62%, rgba(2,5,10,0) 100%)',
      opacity: panel}}>
      <div style={{fontSize: 22, letterSpacing: '0.18em', color: '#dabb86'}}>{body.english}</div>
      <div style={{fontSize: 64, fontWeight: 350, lineHeight: 1.3, marginTop: 12}}>{body.name}</div>
      <div style={{fontSize: 28, color: '#dabb86', marginTop: 14}}>{body.kind}</div>
      <div style={{fontSize: 34, lineHeight: 1.6, marginTop: 25}}>{String(config.props.caption ?? body.feature)}</div>
      <div style={{fontSize: 26, color: '#a7b5c2', marginTop: 20}}>{'轨道距离与天体大小经过艺术压缩'}</div>
    </div>
    {(active === 'oort') && <div style={{position: 'absolute', left: 70, top: 185, fontSize: 34,
      color: '#cfe0f2', lineHeight: 1.5}}>奥尔特云 · 包围太阳系的遥远彗星库
      <div style={{fontSize: 25, color: '#a7b5c2'}}>蓝色内边界为日球层顶，外侧粒子为奥尔特云艺术示意</div></div>}
    <div style={{position: 'absolute', left: 70, top: safe.y - 132, fontSize: 26, color: '#cfe0f2',
      letterSpacing: '0.06em'}}>{body.distance}</div>
    <div style={{position: 'absolute', left: 70, right: 70, top: safe.y - 60, display: 'flex',
      justifyContent: 'space-between', fontSize: 20, color: '#a3b2c0',
      opacity: opening || closing ? fade : 0}}>
      <span>三维艺术示意 · 轨道距离压缩 · 天体放大 · 非实时位置 · 艺术示意</span>
      <span>NASA / JPL / USGS · Solar System Scope（CC BY 4.0）</span>
    </div>
  </div>;
}
