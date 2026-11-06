import type {CSSProperties, ReactNode} from 'react';

/** 代码场景中的整屏容器，与 Remotion composition 无关。 */
export function SceneFill({children, style}: {children?: ReactNode; style?: CSSProperties}) {
  return <div style={{position: 'absolute', inset: 0, width: '100%', height: '100%', ...style}}>{children}</div>;
}
