import {Canvas} from 'm2v/code-scene';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import LifeWorld from './world';
import {actAt} from './lifeMath';

type CopyItem = {id: string; text: string; from: number; to: number; size: number; tone: string; align: string;
  x: number; y: number; width: number; weight: number; spacing: number};
type LifeProps = {copy: CopyItem[]; labels: {choices: string[]}};

const toneColor: Record<string, string> = {primary: '#f4f7fb', secondary: '#afbdca', accent: '#b9ddf5'};

function CopyLayer({copy, t}: {copy: CopyItem[]; t: number}) {
  return <div style={{position: 'absolute', inset: 0, zIndex: 2, pointerEvents: 'none'}}>
    {copy.map((item) => {
      const enter = Math.max(0, Math.min(1, (t - item.from) / 0.45));
      const leave = item.to >= 59.9 ? 1 : Math.max(0, Math.min(1, (item.to - t) / 0.5));
      const opacity = enter * leave;
      if (opacity < 0.01) return null;
      return <div key={item.id} style={{position: 'absolute', left: item.x, top: item.y, width: item.width,
        color: toneColor[item.tone] ?? toneColor.primary, fontSize: item.size, fontWeight: item.weight,
        letterSpacing: item.spacing, lineHeight: 1.12, opacity, textAlign: item.align as 'left' | 'center' | 'right',
        textShadow: '0 3px 24px rgba(0,0,0,.85)', whiteSpace: 'pre-wrap'}}>{item.text}</div>;
    })}
  </div>;
}

export default function Life(config: CodeSceneProps) {
  const clock = useSceneContext();
  const props = config.props as unknown as LifeProps;
  if (!props || !Array.isArray(props.copy) || !props.labels?.choices) {
    throw new Error('人生五选择缺少 copy 或 choices');
  }
  const t = clock.elapsedSeconds;
  const act = actAt(t);
  return <div style={{position: 'relative', width: config.width, height: config.height, overflow: 'hidden', background: '#02060a'}}>
    <Canvas
      dpr={config.captureScale ?? 1}
      shadows
      gl={{antialias: true, alpha: false, powerPreference: 'high-performance'}}
      camera={{position: [5.5, 2.0, 7.5], fov: 36, near: 0.08, far: 2000}}
      onCreated={({gl}) => {
        gl.setClearColor('#02060a', 1);
        gl.toneMappingExposure = 1.04;
        clock.ready();
      }}
    >
      <LifeWorld t={t}/>
    </Canvas>
    <div aria-hidden="true" style={{position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
      background: 'radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 42%, rgba(0,0,0,.30) 100%)'}}/>
    <CopyLayer copy={props.copy} t={t}/>
    <div aria-hidden="true" data-act={act} style={{display: 'none'}}/>
  </div>;
}
