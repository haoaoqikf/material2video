/**
 * 可选二维绘制层。作品按需显式导入；不导入时画面与没有这一层时相同。
 *
 * 用途：辉光质感、高密度粒子、线条生长、逐字显影这类镜头。
 * 载体选择：需要可选中文本与就地排版时用 DOM/SVG；需要真实三维与后期时用
 * `three`；中间这一档才用它。
 *
 * 关键约束见 `frame.ts` 与 `code-scene-runtime.md`：不读挂钟与随机源、不内置
 * 主题、绘制与量测代理共用同一份数据。
 */
export {Painter, type Mark, type Point, type ShapeOptions, type TextOptions, type GroupOptions}
  from './frame';
export {compose, type BloomOptions, type ComposeOptions} from './bloom';
export {MeasureProxy, reviewState, type ReviewState} from './measure-proxy';
export {PainterCanvas, type PainterCanvasProps, type PainterFrame} from './usePainter';
