/**
 * 通用作品的开场场景（初始化生成，可自由改写）。
 *
 * 作品代码控制整张画布：这里自己画不透明背景、自己排版，并在字体与素材就绪后
 * 调用 `ready()`。没有调用会被录制超时拦下，而不是安静地录出一段静止画面。
 *
 * 只允许导入 `m2v/code-scene`、本作品内的文件，以及批准的共享依赖
 * （react、motion、gsap、echarts、three 与 react-three-fiber/drei）。
 */
import {useEffect, useRef} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export default function Opening({props, width, height, subtitleSafeArea}: CodeSceneProps) {
  const {ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    ready();
  }, [ready]);

  const title = typeof props.title === 'string' && props.title ? props.title : '开场';
  const frameNote = `当前画幅 ${width}×${height}；字幕安全区自 ${subtitleSafeArea.y}px 起，高 ${subtitleSafeArea.height}px`;
  return (
    <div style={{width, height, position: 'relative', overflow: 'hidden', background: '#0b0d12', color: '#f4f7fb'}}>
      <div style={{position: 'absolute', left: subtitleSafeArea.x, right: subtitleSafeArea.x,
        top: height * 0.34, fontSize: Math.round(height * 0.072), fontWeight: 700, lineHeight: 1.25}}>
        {title}
      </div>
      {/* 重要文字与主体避让字幕安全区；背景可以延伸到其中。 */}
      <div style={{position: 'absolute', left: subtitleSafeArea.x, right: subtitleSafeArea.x,
        top: height * 0.34 + Math.round(height * 0.1), fontSize: Math.round(height * 0.028), color: '#9aa6b8'}}>
        {frameNote}
      </div>
    </div>
  );
}
