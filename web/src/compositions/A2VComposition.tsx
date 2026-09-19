import type { CSSProperties } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { parseSceneData, type Storyboard } from '@/schema/storyboard';
import { sceneAt } from '@/runtime/timeline';

export type A2VProps = Storyboard;

/**
 * article2video 的主 composition。
 *
 * props **就是分镜本身**（不套一层 `{ storyboard }`）：这样渲染入口可以直接
 * `--props <storyboard.json>`，不需要先生成一个包装文件。分镜是内容层的单一真源，
 * 让它的形状与 props 的形状一致，少一层转换就少一处可能不一致的地方。
 *
 * **当前是阶段 1 的最小实现**：它已经把时间轴、主题作用域与幕容器接好了，
 * 但幕内画面还是占位（帧号 + 幕号）。真正的画面在阶段 2 起由组件注册表接管——
 * 那时这里会调用注册表，而不是画占位。
 *
 * 已经被后续阶段依赖、因此现在就必须正确的三件事：
 *
 * 1. **幕容器带 `data-a2v-scene` 与 `data-scene-id`**：体检的组件契约探针按这两个
 *    属性找幕，改名会让探针静默跳过；
 * 2. **画面上有且只有一个幕被渲染**：渲染是随机访问帧，不能靠「上一帧画了什么」；
 * 3. **预设作用域**：`data-a2v-preset` 只在分镜显式声明时设置，未声明时不留痕迹，
 *    这样令牌与基元规则匹配不到任何元素。
 */
export const A2VComposition: React.FC<A2VProps> = (storyboard) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const span = sceneAt(storyboard, frame);
  const data = parseSceneData(span.scene);
  const theme = storyboard.visual?.theme ?? 'dark';
  const preset = storyboard.visual?.preset;

  const stageStyle = {
    width: storyboard.width,
    height: storyboard.height,
    // 主题作用域：令牌层按它换肤，未声明预设时它不参与
    '--a2v-fps': String(fps),
  } as CSSProperties;

  return (
    <AbsoluteFill>
      <div
        className="a2v-stage"
        data-a2v-stage=""
        data-a2v-theme={theme}
        {...(preset ? { 'data-a2v-preset': preset } : {})}
        style={stageStyle}
      >
        <section
          data-a2v-scene=""
          data-scene-id={span.scene.id}
          data-a2v-scene-type={span.scene.type}
          style={{ position: 'absolute', inset: 0 }}
        >
          <ScenePlaceholder
            sceneId={span.scene.id}
            sceneType={span.scene.type}
            sceneIndex={span.index}
            sceneCount={storyboard.scenes.length}
            localFrame={span.localFrame}
            durationInFrames={span.scene.durationInFrames}
            kicker={span.scene.visual?.kicker}
            data={data}
          />
        </section>
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
  kicker?: string;
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
  kicker,
  data,
}) => {
  const primary = primaryTextOf(data);
  const progress = durationInFrames > 0 ? localFrame / durationInFrames : 0;

  return (
    <div className="a2v-safe" data-a2v-figure="">
      {kicker ? (
        <div
          style={{
            fontSize: 40,
            letterSpacing: '0.14em',
            color: 'rgba(244,247,251,0.66)',
          }}
        >
          {kicker}
        </div>
      ) : null}
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
