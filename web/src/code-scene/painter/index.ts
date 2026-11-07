/**
 * 可选二维绘制层。作品按需显式导入；不导入时画面与没有这一层时相同。
 *
 * 用途：辉光质感、高密度粒子、线条生长、逐字显影这类镜头。
 * 载体选择：需要可选中文本与就地排版时用 DOM/SVG；需要真实三维与后期时用
 * `three`；中间这一档才用它。
 *
 * 关键约束见 `frame.ts` 与 `code-scene-runtime.md`：不读挂钟与随机源、不内置
 * 画面由作品主题数据与受控帧时间共同驱动。
 */
export {Painter, type Point, type ShapeOptions, type TextOptions, type GroupOptions}
  from './frame';
export {keyframeAt, type NumericKey, type NumericInterpolation} from './keyframes';
export {cameraAt, project, type CameraEasing, type CameraKey, type CameraState} from './camera';
export {compose, type BloomOptions, type ComposeOptions} from './bloom';
export {PainterCanvas, type PainterCanvasProps, type PainterFrame} from './usePainter';
