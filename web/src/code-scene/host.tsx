import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {SceneContextProvider, type CodeSceneProps} from './sdk';
import {ensureFonts, FONT_STACK} from '../fonts';
import {palettes} from '../palette';

declare global {
  interface Window {
    __M2V_CODE__: {ready: boolean; start: () => void};
    __M2V_CODE_CONFIG__: CodeSceneProps;
  }
}

export function mount(Component: React.ComponentType<CodeSceneProps>) {
  const config = window.__M2V_CODE_CONFIG__;
  // 实时录制只产出不带透明通道的视频，因此录制页必须自己画上主题背景，
  // 否则片段会以合成器的白色底混进深色成片，浅色作品文字也随之消失。
  const palette = palettes[config.theme];
  document.body.style.background = palette.bg;
  document.body.style.color = palette.ink;
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
