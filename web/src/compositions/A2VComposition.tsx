import { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { parseSceneData, type Storyboard } from '@/schema/storyboard';
import { sceneAt, sceneStartFrames } from '@/runtime/timeline';

export type A2VProps = Storyboard;

/**
 * article2video 的主 composition。
 *
 * props **就是分镜本身**（不套一层 `{ storyboard }`）：这样渲染入口可以直接
 * `--props <storyboard.json>`，不需要先生成一个包装文件。分镜是内容层的单一真源，
 * 让它的形状与 props 的形状一致，少一层转换就少一处可能不一致的地方。
 *
 * **当前是阶段 1 的最小实现**：时间轴、主题作用域、幕容器与锚点已经接好，
 * 幕内画面还是占位（主文案 + 帧号）。真正的画面在组件迁移阶段由注册表接管——
 * 那时改的是 `.a2v-safe` 里画什么，外面的结构与锚点不动。
 *
 * 四件被后续阶段与既有判定逻辑依赖、因此现在就必须正确的事：
 *
 * 1. **所有幕都留在 DOM 里，同一时刻只有一幕可见**。这一条不是实现细节：
 *    动效量测按 `[data-a2v-scene]` 的**下标**定位第 N 幕（`motion.sweep`），
 *    只渲染当前幕会让下标 1 之后全部取到 `undefined`，扫描直接崩在页面里；
 *    隐藏方式也必须与旧页面一致（`display: none`），因为探针是按
 *    「第一个非隐藏的幕」判定当前幕的；
 * 2. **锚点名字照抄旧页面**：`data-a2v-scene` / `data-scene-id` / `.a2v-safe` /
 *    `data-a2v-figure` / `.a2v-scene-index`。改名不会报错，只会让闸门**静默跳过**——
 *    空转的检查与通过的检查在报告里长得一模一样；
 * 3. **`data-a2v-preset` 挂在舞台的祖先上**：探针用的是
 *    `[data-a2v-preset] [data-a2v-stage]`（后代选择器），挂在舞台自身上匹配不到；
 *    未声明预设时这个属性完全不出现，令牌与基元规则因此不命中任何元素；
 * 4. **画面只由帧号推导**：这里没有 CSS 动画、没有真实时钟，改动时也不许引入。
 */
export const A2VComposition: React.FC<A2VProps> = (storyboard) => {
  const frame = useCurrentFrame();
  // 幕起点由时长累加得到（分镜里没有起始帧字段），因此这里只需要下标 → 起点的映射
  const starts = useMemo(() => sceneStartFrames(storyboard), [storyboard]);
  const activeIndex = sceneAt(storyboard, frame).index;
  const theme = storyboard.visual?.theme ?? 'dark';
  const preset = storyboard.visual?.preset;

  const stage = (
    <div className="a2v-stage" data-a2v-stage="" data-a2v-theme={theme}>
      {storyboard.scenes.map((scene, index) => {
        const isActive = index === activeIndex;
        const localFrame = isActive ? Math.min(Math.max(frame - starts[index]!, 0), Math.max(scene.durationInFrames - 1, 0)) : 0;
        const data = parseSceneData(scene);
        return (
          <section
            key={scene.id}
            data-a2v-scene=""
            data-scene-id={scene.id}
            data-layout={scene.visual?.layout ?? 'center'}
            style={isActive ? undefined : { display: 'none' }}
          >
            <ScenePlaceholder
              sceneId={scene.id}
              sceneType={scene.type}
              sceneIndex={index}
              sceneCount={storyboard.scenes.length}
              localFrame={localFrame}
              durationInFrames={scene.durationInFrames}
              data={data}
            />
          </section>
        );
      })}
    </div>
  );

  if (!preset) {
    return <AbsoluteFill>{stage}</AbsoluteFill>;
  }

  // `display: contents`：这一层只为承载 `data-a2v-preset` 而存在，
  // 不生成盒子，因此舞台的尺寸与位置完全不受影响。
  return (
    <AbsoluteFill>
      <div data-a2v-preset={preset} style={{ display: 'contents' }}>
        {stage}
      </div>
    </AbsoluteFill>
  );
};

interface ScenePlaceholderProps {
  sceneId: string;
  sceneType: string;
  sceneIndex: number;
  sceneCount: number;
  localFrame: number;
  durationInFrames: number;
  data: Record<string, unknown>;
}

/**
 * 阶段 1 的占位画面。
 *
 * 它存在的意义是让契约页、体检探针与渲染链路先跑通：探针要能从画面里读到文案，
 * 因此这里把分镜里的主文案画出来（而不是只印一个帧号），
 * 否则「探针读不到文案」会被误判成探针坏了。
 */
const ScenePlaceholder: React.FC<ScenePlaceholderProps> = ({
  sceneId,
  sceneType,
  sceneIndex,
  sceneCount,
  localFrame,
  durationInFrames,
  data,
}) => {
  const primary = primaryTextOf(data);
  const progress = durationInFrames > 0 ? localFrame / durationInFrames : 0;

  return (
    <div className="a2v-safe" data-a2v-figure="">
      <div
        style={{
          marginTop: 48,
          fontSize: 96,
          lineHeight: 1.2,
          fontWeight: 700,
        }}
      >
        {primary}
      </div>
      <div
        style={{
          marginTop: 48,
          fontSize: 40,
          color: 'rgba(244,247,251,0.72)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {`第 ${sceneIndex + 1} / ${sceneCount} 幕 · ${sceneType} · ${sceneId}`}
      </div>
      <div
        data-a2v-placeholder-frame=""
        style={{
          marginTop: 16,
          fontSize: 40,
          color: 'rgba(244,247,251,0.72)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {`幕内第 ${localFrame} 帧 · 进度 ${progress.toFixed(3)}`}
      </div>
    </div>
  );
};

/** 取该幕的主文案，供占位与探针使用。 */
function primaryTextOf(data: Record<string, unknown>): string {
  for (const key of ['text', 'title', 'label'] as const) {
    const value = data[key];
    if (typeof value === 'string' && value.length > 0) {
      return value;
    }
  }
  const left = data['left'];
  const right = data['right'];
  if (typeof left === 'string' && typeof right === 'string') {
    return `${left} → ${right}`;
  }
  const items = data['items'];
  if (Array.isArray(items) && items.length > 0) {
    const first = items[0];
    if (typeof first === 'string') {
      return first;
    }
    if (first && typeof first === 'object' && 'label' in first) {
      const label = (first as { label?: unknown }).label;
      if (typeof label === 'string') {
        return label;
      }
    }
  }
  const nodes = data['nodes'];
  if (Array.isArray(nodes) && nodes.length > 0) {
    const first = nodes[0];
    if (typeof first === 'string') {
      return first;
    }
    if (first && typeof first === 'object' && 'id' in first) {
      const id = (first as { id?: unknown }).id;
      if (typeof id === 'string') {
        return id;
      }
    }
  }
  return '（这一幕没有可显示的主文案）';
}
