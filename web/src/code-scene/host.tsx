import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {flushSync} from 'react-dom';
import {SceneContextProvider, type CodeSceneProps} from './sdk';
import {ensureFonts, FONT_STACK} from '../fonts';

declare global {
  interface Window {
    __M2V_CODE__: {
      ready: boolean; start: () => void;
      advanceToFrame: (frame: number) => Promise<void>;
      advanceToSubframe: (frame: number, subframe: number, subframes: number) => Promise<void>;
    };
    __M2V_CAPTURE_CLOCK__: {
      begin: () => void;
      setTime: (milliseconds: number) => void;
      flush: () => Promise<void>;
      bootstrap: () => Promise<void>;
    };
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
  const unavailable = () => {throw new Error('场景尚未挂载');};
  window.__M2V_CODE__ = {ready: false, start: unavailable, advanceToFrame: unavailable,
    advanceToSubframe: unavailable};
  function Host() {
    const [running, setRunning] = useState(false);
    const [elapsedSeconds, setElapsed] = useState(0);
    useEffect(() => {
      let last = {frame: -1, subframe: -1, subframes: 1};
      let started = false;
      window.__M2V_CODE__.start = () => {
        if (started || !window.__M2V_CODE__.ready) throw new Error('录制启动状态无效');
        started = true;
        window.__M2V_CAPTURE_CLOCK__.begin();
        flushSync(() => setRunning(true));
      };
      // 只接受连续推进：同一帧内子帧递增，或进入下一帧的第 0 个子帧。
      // 子帧时间是 (frame + subframe / subframes) / fps，因此 React 状态、三维绘制、
      // 动画库、CSS 动画与本地视频都停在同一个真实时刻上——这是运动模糊成立的前提。
      const advance = async (frame: number, subframe: number, subframes: number) => {
        const continuous = (frame === last.frame && subframes === last.subframes && subframe === last.subframe + 1)
          || (frame === last.frame + 1 && subframe === 0);
        if (!started || !Number.isInteger(frame) || !Number.isInteger(subframe)
            || !Number.isInteger(subframes) || subframes < 1 || subframe < 0 || subframe >= subframes
            || frame < 0 || frame >= config.durationInFrames || !continuous) {
          throw new Error(`录制只接受连续帧号，收到 ${frame}+${subframe}/${subframes}，`
            + `上一帧 ${last.frame}+${last.subframe}/${last.subframes}`);
        }
        const position = frame + subframe / subframes;
        window.__M2V_CAPTURE_CLOCK__.setTime(position * 1000 / config.fps);
        flushSync(() => setElapsed(position / config.fps));
        await window.__M2V_CAPTURE_CLOCK__.flush();
        last = {frame, subframe, subframes};
      };
      window.__M2V_CODE__.advanceToFrame = frame => advance(frame, 0, 1);
      window.__M2V_CODE__.advanceToSubframe = (frame, subframe, subframes) => advance(frame, subframe, subframes);
    }, []);
    // 全局时间是 opt-in：未声明 capture.timebase=global 时两者退化为幕内时间，
    // 既有作品看到的数值与行为不变。
    const sceneStartFrame = config.timeline?.sceneStartFrame ?? 0;
    const globalFrame = sceneStartFrame + elapsedSeconds * config.fps;
    const globalSeconds = sceneStartFrame / config.fps + elapsedSeconds;
    return <SceneContextProvider.Provider value={{running, elapsedSeconds, globalFrame, globalSeconds,
      sceneStartFrame,
      progress: Math.min(1, elapsedSeconds * config.fps / config.durationInFrames),
      ready: () => {void ensureFonts().then(() => document.fonts.ready).then(() => {window.__M2V_CODE__.ready = true;});}}}>
      <Component {...config}/>
    </SceneContextProvider.Provider>;
  }
  createRoot(document.getElementById('root')!).render(<Host/>);
}
