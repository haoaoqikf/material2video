/**
 * 图表的数据侧：从分镜读序列、按帧号算切片——全部是纯函数（任务 7.1 / 7.2）。
 *
 * 「逐帧数据切片」的含义：ECharts 每一帧收到的 option 只描述**当前帧**该画什么
 * ——柱子长到多高、折线推进到哪、饼图张开多少。我们不把「完整数据 + 动画时长」
 * 交给图表库让它在自己的时钟上补间，而是用动效配方层的同一条缓动曲线把补间
 * 从它手里拿回来。这样图表与其它组件共用一条时间线：
 * 同一帧重复求值必然一致，任意帧随机访问与顺序播放一致。
 *
 * 两条来自既有契约的约束：
 * - **坐标轴不参与动画**：轴的范围由**完整数据**算出（`AXIS_EXTENT…`），
 *   切片只改 series 的数据。轴跟着切片缩放的话，柱子没长、轴先伸缩，
 *   观众读到的数值刻度每帧都在变——那不是动效，是画面不稳定。
 * - **DOM 文本显示最终值**（任务 7.4）：画面上可读的文字必须等于最终值，
 *   与数字幕 `ROLL_MIN` 的理由相同；逐帧滚动只发生在 canvas 内部。
 */
import { EASE } from '@/runtime/figures';
import { lerp, motionBeat, progress, type MotionState } from '@/runtime/motion';

/** 本工程支持的图表类型。新增类型要同时扩 `echarts.ts` 的注册清单。 */
export type ChartType = 'bar' | 'line' | 'pie';

export const CHART_TYPES: readonly ChartType[] = ['bar', 'line', 'pie'];

/** 分镜里的图表类型声明（`data.chart`）。缺省柱状——最不容易读错的一种。 */
export function parseChartType(raw: unknown): ChartType {
  if (raw === null || raw === undefined || raw === '') {
    return 'bar';
  }
  if (typeof raw === 'string' && (CHART_TYPES as readonly string[]).includes(raw)) {
    return raw as ChartType;
  }
  throw new Error(
    `图表类型只支持 ${CHART_TYPES.join(' / ')} 之一，实际为 ${String(raw)}`,
  );
}

export interface ChartPoint {
  label: string;
  value: number;
}

/**
 * 从分镜读数据序列。组件里**没有默认数据**（任务 7.2 的静态机检盯着这一条）：
 * 缺数据、空序列、非法条目都在这里报错——「画不出来要报错」，不画空白。
 */
export function parseChartPoints(raw: unknown): ChartPoint[] {
  if (!Array.isArray(raw) || raw.length === 0) {
    throw new Error(
      'chart 场景需要非空的 values 数组，每项形如 {"label": "四月", "value": 12}',
    );
  }
  return raw.map((item, index) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      throw new Error(`values[${index}] 必须是 {"label", "value"} 对象`);
    }
    const record = item as Record<string, unknown>;
    const label = record['label'];
    const value = record['value'];
    if (typeof label !== 'string' || !label.trim()) {
      throw new Error(`values[${index}].label 必须是非空字符串`);
    }
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new Error(`values[${index}].value 必须是有限数字`);
    }
    return { label: label.trim(), value };
  });
}

/**
 * 显影节奏：第 i 个点从幕的 `START_FRACTION` 比例点起、按 `STAGGER_FRAMES`
 * 错开，在 `DURATION_FRAMES` 帧内走完 outQuint。
 *
 * 这三个数就是图表的全部「动效配方」，与其它组件一样只取配方层的曲线，
 * 组件里不写自然周期或阻尼——整支片子的手感只在一处调。
 */
export const REVEAL_TIMING = {
  START_FRACTION: 0.08,
  STAGGER_FRAMES: 4,
  DURATION_FRAMES: 26,
} as const;

/** 每个数据点的显影进度（0..1），下标与 `parseChartPoints` 的结果对齐。 */
export function revealProgresses(state: MotionState, count: number): number[] {
  const start = motionBeat(state, REVEAL_TIMING.START_FRACTION);
  const out: number[] = [];
  for (let index = 0; index < count; index += 1) {
    out.push(progress(state.localFrame, start + index * REVEAL_TIMING.STAGGER_FRAMES, REVEAL_TIMING.DURATION_FRAMES, EASE.out));
  }
  return out;
}

/**
 * 显影起点（幕内帧号）：DOM 文本层与 canvas 层共用同一份节奏时的锚点。
 * 单独导出而不是让组件自己再算一遍 `motionBeat`——两处各写一次，
 * 迟早有一处改了节奏值另一处没跟上。
 */
export function revealStartFrame(state: MotionState): number {
  return motionBeat(state, REVEAL_TIMING.START_FRACTION);
}

function clamp01(value: number): number {
  return value < 0 ? 0 : value > 1 ? 1 : value;
}

/** 值域上限：给最大值留出 8% 的头部空间，柱顶/线头的标签不顶到画布边缘。 */
const AXIS_HEADROOM = 1.08;

/**
 * 值域范围由**完整数据**决定，与帧号无关（轴不参与动画）。
 * 下限固定从 0 起算：这类图表比的是数量级，从非零起算会夸大差异；
 * 出现负值时下限压到负向极值，柱子向下生长才有参照。
 */
export function valueExtent(points: ChartPoint[]): { min: number; max: number } {
  let min = 0;
  let max = 0;
  for (const point of points) {
    if (point.value < min) {
      min = point.value;
    }
    if (point.value > max) {
      max = point.value;
    }
  }
  if (max === 0 && min === 0) {
    // 全 0 的序列也要有轴：给一个非零区间，避免空轴与除零
    max = 1;
  }
  return { min, max: max * AXIS_HEADROOM };
}

/** 柱状切片：每根柱按自身进度从 0 长到目标值。 */
export function barSlice(points: ChartPoint[], reveals: number[]): number[] {
  return points.map((point, index) => point.value * clamp01(reveals[index] ?? 0));
}

/** 饼图切片：每个扇区按自身进度张开（半径不变，角度由数值占比决定）。 */
export function pieSlice(points: ChartPoint[], reveals: number[]): number[] {
  return barSlice(points, reveals);
}

/** 折线切片的一个点：x 用数值轴，线头因此能落在两档之间，线是连续生长的。 */
export interface LinePoint {
  x: number;
  y: number;
  /** 线头（显影中的那个点）不画符号：符号只在点「到位」后出现。 */
  tip: boolean;
}

/**
 * 折线切片：已经到位的点原样给出，显影中的线头落在
 * `前一个点的 x + 自身进度` 上、y 取两点间的线性插值——
 * 与 `drawPath` 原语同一条思路：线沿着路径推进，而不是逐段跳出。
 *
 * 第一个点没有前驱，它的 y 从 0 升到目标值（从横轴上长出来）；
 * 这是折线唯一一处「竖直生长」，其余都是沿段推进。
 */
export function lineSlice(points: ChartPoint[], reveals: number[]): LinePoint[] {
  const out: LinePoint[] = [];
  for (let index = 0; index < points.length; index += 1) {
    const p = clamp01(reveals[index] ?? 0);
    if (p <= 0) {
      // 进度按下标错开，遇到 0 就说明后面都还没显影
      break;
    }
    const point = points[index]!;
    const previous = points[index - 1];
    if (p >= 1 || !previous) {
      out.push({ x: index, y: p >= 1 ? point.value : point.value * p, tip: p < 1 });
      continue;
    }
    out.push({
      x: index - 1 + p,
      y: lerp(previous.value, point.value, p),
      tip: true,
    });
  }
  return out;
}

/** 数值 → 画面文本。千分位 + 去掉浮点尾数；单位由调用方拼在后面。 */
export function formatValue(value: number): string {
  const rounded = Math.abs(value) >= 1000 ? Math.round(value) : Math.round(value * 100) / 100;
  return rounded.toLocaleString('en-US', { maximumFractionDigits: 2 });
}
