import { useLayoutEffect, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { parseSceneData, type Scene, type Storyboard } from '@/schema/storyboard';
import { FigureProvider, createFigureApi, pad, type FigureSpec } from '@/runtime/figures';
import { figureDefinition, knownKinds, resolveKind } from '@/registry';
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
 * 3. **主题与预设挂在 `<html>` 上**，与旧页面（`assets/declarative.js`）逐字一致：
 *    `data-a2v-theme` / `data-a2v-preset` / 行内的 `--a2v-width`、`--a2v-height`
 *    都写在 `document.documentElement` 上。挂到舞台自身上会漏掉两类规则——
 *    一类是 `:root[data-a2v-preset="keynote"]` 这种把根元素写进选择器的令牌块，
 *    另一类是 `[data-a2v-preset] [data-a2v-stage]` 这类要求属性在祖先上的规则。
 *    漏掉的症状是「预设的排版与令牌整片不生效」，而校验与渲染都照常通过。
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

  /*
   * 舞台尺寸与主题写在根元素上：契约页与 Remotion 渲染页都是真实浏览器页面，
   * `documentElement` 就是旧页面里那个 `<html>`。这一步不参与逐帧计算
   * （只在 props 变化时执行），因此不影响帧驱动的确定性。
   */
  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.a2vTheme = theme;
    if (preset) {
      root.dataset.a2vPreset = preset;
    } else {
      delete root.dataset.a2vPreset;
    }
    root.style.setProperty('--a2v-width', `${storyboard.width}px`);
    root.style.setProperty('--a2v-height', `${storyboard.height}px`);
  }, [theme, preset, storyboard.width, storyboard.height]);

  const stage = (
    <div className="a2v-stage" data-a2v-stage="">
      {/*
        舞台底纹三层，顺序与旧页面一致（`assets/declarative.html` 的
        `glow → grid → grain`）：它们是**画面的一部分**，不是页面装饰——
        底色、光晕与颗粒都会被抽帧对照算进像素差。少一层或换个顺序，
        画面就只是「看起来差不多」。
      */}
      <div className="a2v-bg-glow stage-bg" aria-hidden="true" />
      <div className="a2v-bg-grid stage-bg" aria-hidden="true" />
      <div className="a2v-bg-grain stage-bg" aria-hidden="true" />
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
            <SceneFigure
              scene={scene}
              sceneIndex={index}
              sceneCount={storyboard.scenes.length}
              fps={storyboard.fps}
              preset={preset}
              active={isActive}
              localFrame={localFrame}
              data={data}
            />
            {/*
              幕角标只在预设生效时出现（旧页面同样如此）：它写着作者给的定位词与幕号。
              没写 kicker 时留一个空 span 而**不回落到类型名**——`TITLE` 这种内部
              标识符不是给读者看的字；也不能删掉整个 span，那一行是
              `justify-content: space-between`，少一个子元素会把幕号从右边甩到左边。
            */}
            {preset ? (
              <div className="a2v-scene-index">
                <span>{String(scene.visual?.kicker ?? '').trim()}</span>
                <span className="a2v-scene-number">{`${pad(index + 1)} / ${pad(storyboard.scenes.length)}`}</span>
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );

  return <AbsoluteFill>{stage}</AbsoluteFill>;
};

interface SceneFigureProps {
  scene: Scene;
  sceneIndex: number;
  sceneCount: number;
  fps: number;
  preset: string | undefined;
  /** 这一幕此刻是否可见；取档依赖它（`display: none` 的元素量出来是 0） */
  active: boolean;
  localFrame: number;
  data: Record<string, unknown>;
}

/**
 * 一幕的画面：按注册表取组件，把这一幕的状态交给它。
 *
 * 组件拿到的是**只读的运行时**（帧号、幕长、节奏、分镜数据、标注、动效接口），
 * 它自己不去查 DOM、不读全局变量、不碰计时器——画面因此只由帧号与分镜决定。
 *
 * 取不到组件时抛错而不是画空白：`kind` 写错、或场景类型没有默认组件，
 * 都是「这条分镜画不出来」，静默空白会让它在成片里才被发现。
 */
const SceneFigure: React.FC<SceneFigureProps> = ({
  scene,
  sceneIndex,
  sceneCount,
  fps,
  preset,
  active,
  localFrame,
  data,
}) => {
  const kind = resolveKind(scene.type, data);
  const declared = (data['figure'] ?? {}) as Record<string, unknown>;
  const annotations = (data['annotations'] ?? {}) as Record<string, string>;
  const labels = (declared['labels'] ?? annotations) as Record<string, string>;
  const spec: FigureSpec = {
    kind: kind ?? '',
    labels: labels ?? {},
    params: (declared['params'] ?? {}) as Record<string, unknown>,
    motion: typeof declared['motion'] === 'string' ? declared['motion'] : 'normal',
  };
  const state = {
    localFrame,
    sceneDurationFrames: scene.durationInFrames,
    motion: spec.motion,
  };
  const definition = kind ? figureDefinition(kind) : undefined;

  if (!kind || !definition) {
    throw new Error(
      `场景 ${scene.id} 画不出来：kind=${kind ?? '(未声明)'}，` +
        `类型 ${scene.type} 也没有默认组件（已注册：${knownKinds().join('、')}）`,
    );
  }

  const Figure = definition.Component;
  return (
    <div className="a2v-safe" data-a2v-figure="" data-fig-kind={kind}>
      <FigureProvider
        value={{
          scene,
          sceneIndex,
          sceneCount,
          data,
          spec,
          fps,
          preset,
          active,
          state,
          api: createFigureApi(fps),
        }}
      >
        <Figure />
      </FigureProvider>
    </div>
  );
};
