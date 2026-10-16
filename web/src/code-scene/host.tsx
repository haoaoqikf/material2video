import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {SceneContextProvider, type CodeSceneProps} from './sdk';
import {ensureFonts, FONT_STACK} from '../fonts';

declare global {
  interface Window {
    __M2V_CODE__: {ready: boolean; start: () => void};
  }
}

export function mount(Component: React.ComponentType<CodeSceneProps>) {
  const injected = window.__M2V_CODE_CONFIG__;
  if (!injected) throw new Error('代码场景录制页缺少运行时配置');
  // 去掉可选的 media 后再下传：作品通过 useMediaAsset 取素材，不直接读全局。
  const config: CodeSceneProps = injected;
  // 录制页不再按主题设置前景与背景：画幅、配色与构图都由作品代码决定，作品必须在
  // 调用 `ready()` 之前自己铺满整张画布并画上不透明背景。页面底色只是编码兜底，
  // 不是作品主题——没有铺满的作品会在成片里留出这块底色。
  document.body.style.fontFamily = FONT_STACK;
  window.__M2V_CODE__ = {ready: false, start: () => {throw new Error('场景尚未挂载');}};
  function Host() {
    const [running, setRunning] = useState(false);
    const [elapsedSeconds, setElapsed] = useState(0);
    useEffect(() => {
      window.__M2V_CODE__.start = () => setRunning(true);
    }, []);
    useEffect(() => {
      if (!running) return;
      const start = performance.now();
      let handle = 0;
      const tick = () => {setElapsed((performance.now() - start) / 1000); handle = requestAnimationFrame(tick);};
      handle = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(handle);
    }, [running]);
    return <SceneContextProvider.Provider value={{running, elapsedSeconds,
      progress: Math.min(1, elapsedSeconds * config.fps / config.durationInFrames),
      ready: () => {void ensureFonts().then(() => document.fonts.ready).then(() => {window.__M2V_CODE__.ready = true;});}}}>
      <Component {...config}/>
    </SceneContextProvider.Provider>;
  }
  createRoot(document.getElementById('root')!).render(<Host/>);
}
