/** 可执行异步绘制示例；由真实浏览器测试核验帧等待、定位及失败边界。 */
import {useLayoutEffect, useRef} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export default function AsyncBitmap(config: CodeSceneProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const {elapsedSeconds, running, ready, waitForFrame} = useSceneContext();
  useLayoutEffect(() => {
    const position = elapsedSeconds * config.fps;
    const draw = async () => {
      const source = new OffscreenCanvas(config.width, config.height);
      const context = source.getContext('2d')!;
      context.fillStyle = `rgb(${Math.round(31 + position * 12)},81,119)`;
      context.fillRect(0, 0, config.width, config.height);
      const bitmap = await createImageBitmap(await source.convertToBlob());
      try {
        if (position === config.props.rejectFrame) throw new Error('async-bitmap-failure');
        canvas.current!.getContext('2d')!.drawImage(bitmap, 0, 0);
      } finally {bitmap.close();}
    };
    waitForFrame(draw());
    if (!running) {ready(); ready();}
  }, [elapsedSeconds, running, config.width, config.height, config.fps, config.props.rejectFrame]);
  return <canvas ref={canvas} width={config.width} height={config.height}/>;
}
