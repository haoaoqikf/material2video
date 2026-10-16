import {useCallback, useMemo, useRef} from 'react';
import {type CodeSceneProps} from 'm2v/code-scene';
import {BODIES, CHAPTER_IDS, CHAPTERS} from './bodies';
import {useNarration} from './clock';
import {poseAt} from './layout';
import {useTextures, useTextureSources} from './world';
import {SolarSystem, type LiveScene} from './solar-system';
import {Labels} from './labels';

export default function Journey(config: CodeSceneProps) {
  const clock = useNarration(config);
  const ids = config.props.targets as string[];
  const stops = useMemo(() => Object.values(config.segmentWindows).map((w, i) => ({
    id: ids[i], start: w.startFrame / config.fps, end: w.endFrame / config.fps,
  })), [config.segmentWindows, config.fps, ids]);
  const id = ids[clock.index];
  if (!BODIES[id]) throw new Error(`未知天体：${id}`);
  const body = BODIES[id];
  const chapter = Object.keys(config.segmentWindows)[clock.index].split('-')[0];
  const chapterIndex = CHAPTER_IDS.indexOf(chapter);
  const sources = useTextureSources();
  const textures = useTextures(sources);
  const ready = useRef(clock.ready);
  ready.current = clock.ready;
  const onReady = useCallback(() => ready.current(), []);
  const pose = poseAt(stops, clock.index, clock.elapsedSeconds);
  // R3F 与 DOM 共用最新时钟引用。高频运动直接更新网格，不逐帧重建 React 场景树。
  const live = useRef<LiveScene>({seconds: clock.elapsedSeconds, pose});
  live.current = {seconds: clock.elapsedSeconds, pose};
  const overview = pose.overview > 0.65;
  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: '#02050a', color: '#f2eee5'}}>
    <div style={{position: 'absolute', inset: 0, zIndex: 0}}>
      {textures && <SolarSystem textures={textures} target={id} live={live} onReady={onReady}/>}
    </div>
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
      background: 'linear-gradient(0deg, #02050a 0%, rgba(2,5,10,0.65) 13%, transparent 28%, transparent 83%, rgba(2,5,10,0.9) 100%)'}}/>
    <Labels pose={pose} width={config.width} height={config.height} target={id}/>
    <div style={{position: 'absolute', left: 70, right: 70, top: 42, display: 'flex', justifyContent: 'space-between',
      fontSize: 19, letterSpacing: '0.12em', color: '#bdc9d2'}}>
      <span>SOLAR SYSTEM / 太阳系之旅</span><span>{overview ? '完整太阳系 · 空间总览' : `正在靠近 · ${body.name}`}</span>
    </div>
    <div style={{position: 'absolute', left: 70, right: 70, top: 99, display: 'flex', gap: 22}}>
      {CHAPTERS.map((name, index) => <div key={name} style={{fontSize: 17,
        color: index === chapterIndex ? '#e7cca2' : '#8496a8'}}>{index + 1} / {name}</div>)}
    </div>
    <div style={{position: 'absolute', left: 70, top: 410, width: 450, padding: '26px 28px',
      borderLeft: '1px solid #9c8159', background: 'linear-gradient(90deg, rgba(2,5,10,0.97), rgba(2,5,10,0.88))'}}>
      <div style={{fontSize: 17, letterSpacing: '0.18em', color: '#dabb86'}}>{body.english}</div>
      <div style={{fontSize: 64, fontWeight: 350, lineHeight: 1.3, marginTop: 12}}>{body.name}</div>
      <div style={{fontSize: 22, color: '#dabb86', marginTop: 14}}>{body.kind}</div>
      <div style={{fontSize: 23, lineHeight: 1.6, marginTop: 25}}>{body.feature}</div>
      <div style={{fontSize: 19, color: '#a7b5c2', marginTop: 20}}>{body.distance}</div>
    </div>
    <div style={{position: 'absolute', left: 70, right: 70, top: config.subtitleSafeArea.y - 65,
      display: 'flex', justifyContent: 'space-between', fontSize: 16, color: '#a3b2c0'}}>
      <span>同一三维模型 · 轨道距离压缩 · 天体放大 · 非实时位置</span>
      <span>NASA / JPL / USGS · Solar System Scope（CC BY 4.0）· 艺术示意</span>
    </div>
  </div>;
}
