import {useLayoutEffect, useRef} from 'react';
import {createSceneEvents, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export default function EventCapture({eventFrames, fps}: CodeSceneProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const clock = useSceneContext();
  const frame = Math.round(clock.elapsedSeconds * fps);
  const active = frame >= createSceneEvents(eventFrames).frame('hit');

  useLayoutEffect(() => {
    const context = canvas.current?.getContext('2d');
    if (!context) throw new Error('2D canvas unavailable');
    context.fillStyle = '#000';
    context.fillRect(0, 0, 160, 90);
    if (active) {
      context.fillStyle = '#ff0';
      context.fillRect(20, 20, 40, 30);
    }
    clock.ready();
  }, [active, clock.ready]);

  return <canvas ref={canvas} width={160} height={90} />;
}
