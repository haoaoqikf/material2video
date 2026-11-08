/** 本作品的 R3F 画布包装：lookdev 时按采集倍率提高原生像素密度。 */
import {Canvas as FiberCanvas, type CanvasProps} from '@react-three/fiber';

export function Canvas(props: CanvasProps) {
  const scale = window.__M2V_CODE_CONFIG__?.captureScale;
  return <FiberCanvas {...props} dpr={scale ?? props.dpr}/>;
}
