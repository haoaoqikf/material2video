import {useCallback, useMemo, useRef} from 'react';
import type {CodeSceneProps} from '../src/code-scene/context';
import type {Look, Shot} from '../src/code-scene/cinematic/camera';
import {BODIES, CHAPTER_IDS, CHAPTER_OF, CHAPTERS} from './bodies';
import {clamp, useNarration} from './clock';
import {useTextures, useTextureSources} from './world';
import {SolarSystem} from './solar-system';

export function shotAt(shots: Shot[], frame: number): Shot | null {
  return shots.find(shot => frame >= shot.startFrame && frame < shot.endFrame) ?? null;
}

/** 名称在观察期间保留；飞行时退场，不把字幕和资料表同时压在主体旁。 */
function labelOpacity(shot: Shot | null, frame: number, start: number): number {
  if (!shot?.segment) return 0;
  return Math.min(clamp((frame - start) / 24), clamp((shot.endFrame - frame) / 30));
}

export default function Journey(config: CodeSceneProps) {
  const clock = useNarration(config);
  const shots = (config.props.shots ?? []) as Shot[];
  const look = (config.props.look ?? {profile: 'deep-space-cinematic'}) as Look;
  const frame = Math.round(clock.elapsedSeconds * config.fps);
  const shot = useMemo(() => shotAt(shots, frame), [shots, frame]);
  const active = shot && BODIES[shot.target] ? shot.target : 'sun';
  const body = BODIES[active];
  const chapterIndex = Math.max(0, CHAPTER_IDS.indexOf(CHAPTER_OF[active] ?? 'sun'));
  const firstStart = Math.min(...Object.values(config.segmentWindows).map(window => window.startFrame));
  const window = shot?.segment ? config.segmentWindows[shot.segment] : undefined;
  // 日球层顶刚离开时边缘还在视野外，等回望能看到壳缘，再出现其名称。
  const titleStart = window ? window.startFrame + (active === 'heliopause' ? 120 : 0) : Infinity;
  const panel = labelOpacity(shot, frame, titleStart);
  const outer = active === 'heliopause' || active === 'oort';
  const track = clamp(frame / Math.max(1, config.durationInFrames - 1));
  const opening = frame < firstStart;
  const tail = shots.at(-1);
  const credits = opening ? clamp((frame - 12) / 24)
    : tail && frame >= Math.max(tail.startFrame, config.durationInFrames - 300)
      ? clamp((frame - Math.max(tail.startFrame, config.durationInFrames - 300)) / 36) : 0;
  const sources = useTextureSources();
  const textures = useTextures(sources);
  const ready = useRef(clock.ready);
  ready.current = clock.ready;
  const onReady = useCallback(() => ready.current(), []);
  const safe = config.subtitleSafeArea;
  // 只在正文后方保留局部渐变，不让旧信息板的大矩形盖住星体。
  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: '#02050a', color: '#f2eee5'}}>
    <div style={{position: 'absolute', inset: 0}}>
      {textures && <SolarSystem textures={textures} shots={shots} look={look} active={active}
        seconds={clock.elapsedSeconds} fps={config.fps} windows={config.segmentWindows} onReady={onReady}/>}
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 140,
      background: 'linear-gradient(180deg, rgba(2,5,10,0.76), transparent)'}}/>
    {active === 'ceres' && <div style={{position: 'absolute', right: 0, top: 0, width: 340, height: 132,
      opacity: clamp(panel * 1.8), background: 'linear-gradient(180deg, #02050a 46%, transparent)',
      maskImage: 'linear-gradient(270deg, #000 54%, transparent)'}}/>}
    <div style={{position: 'absolute', left: 0, right: 0, top: safe.y - 70, bottom: 0,
      background: 'linear-gradient(180deg, transparent, rgba(2,5,10,0.82))'}}/>
    <div style={{position: 'absolute', left: 88, right: 88, top: 52, display: 'flex',
      justifyContent: 'space-between', fontSize: 24, letterSpacing: '0.12em', color: '#b4bdc6'}}>
      <span>太阳系之旅</span>
      <span style={{color: '#d3bb93'}}>{CHAPTERS[chapterIndex]}</span>
    </div>
    <div style={{position: 'absolute', left: 88, right: 88, top: 101, height: 1,
      background: 'rgba(174,190,205,0.18)'}}>
      <div style={{height: 1, width: `${track * 100}%`, background: '#cbb28b'}}/>
    </div>
    <div style={{position: 'absolute', left: 88, top: outer ? 175 : 375, width: 520,
      opacity: panel, textShadow: '0 2px 24px #02050a'}}>
      <div style={{fontSize: 20, letterSpacing: '0.2em', color: '#bba887'}}>{body.english}</div>
      <div style={{fontSize: outer ? 64 : 82, fontWeight: 350, lineHeight: 1.3, marginTop: 16}}>{body.name}</div>
      <div style={{width: outer ? 64 : 48, height: outer ? 5 : 1, marginTop: 22,
        background: active === 'heliopause' ? body.color : active === 'oort'
          ? `repeating-linear-gradient(90deg, ${body.color} 0 4px, transparent 4px 9px)` : '#cbb28b'}}/>
      <div style={{fontSize: outer ? 34 : 36, lineHeight: 1.65, marginTop: 22, color: '#dfd8cc'}}>
        {body.feature}
      </div>
      {active === 'oort' && <div style={{fontSize: 20, marginTop: 16, color: '#a7b5c2'}}>推测性结构 · 艺术示意</div>}
    </div>
    <div style={{position: 'absolute', left: 88, bottom: 108, fontSize: 40,
      color: '#b4bdc6', opacity: credits}}>
      大小与距离分别压缩 · 非实时位置
      <span style={{fontSize: 20, marginLeft: 20, color: '#8795a2'}}>三维艺术示意</span>
    </div>
    <div style={{position: 'absolute', left: 88, bottom: 48, fontSize: 32,
      color: '#b8c2cc', opacity: credits}}>NASA / JPL / USGS · Solar System Scope（CC BY 4.0）</div>
    {tail && frame >= tail.startFrame && <div style={{position: 'absolute', left: 88, top: 185,
      fontSize: 56, color: '#ddd9d0', opacity: clamp((frame - tail.startFrame) / 48)}}>
      回望太阳，只剩一个亮点
    </div>}
  </div>;
}
