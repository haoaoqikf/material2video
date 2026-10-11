import { StrictMode, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Player, type PlayerRef } from '@remotion/player';
import { M2VComposition } from '@/compositions/M2VComposition';
import { M2VCompositionV4 } from '@/compositions/M2VCompositionV4';
import { ensureFonts } from '@/fonts';
import { parseStoryboard, type Storyboard } from '@/schema/storyboard';
import { storyboardV4Schema, type StoryboardV4 } from '@/schema/storyboardV4';
import { totalFrames } from '@/runtime/timeline';
import { createContract } from './bridge';
import { resolveStoryboardV4 } from '@/runtime/timelineV4';
import type { V4MediaTimeline } from '@/runtime/timelineV4';
import { installOfflineGuard } from '@/runtime/offline-guard';
import '@/styles/index.css';

// 尽早开始加载字体：`ready()` 会等它，但它不必等到那时才开始
void ensureFonts();
// 运行期隔离：契约页路径对非本地请求先阻断，违规由体检读出并计为失败
installOfflineGuard();

/**
 * 渲染契约页。
 *
 * 职责只有一件：把 composition 挂进一个**可被 Playwright 驱动的页面**，
 * 并暴露 `window.__M2V__`（v4 分镜为 version 4）。
 * 体检与量测全部通过它工作。
 *
 * composition 按分镜声明的契约版本在**运行时**选择，而不是由构建期的
 * 生成入口写死：契约页是共享的，一次构建要能服务任意作品；把版本绑到
 * 构建产物上，会让「先构建了哪个版本」决定页面能渲染哪个契约，
 * 换一个作品就要重建、并在构建失败时以空白首帧的形式混进评审。
 */
function ContractApp(): React.ReactElement {
  const params = new URLSearchParams(window.location.search);
  const storyboardUrl = params.get('m2v-storyboard');
  const playerRef = useRef<PlayerRef>(null);
  const [loaded, setLoaded] = useState<{ storyboard: Storyboard | StoryboardV4; mediaTimeline?: V4MediaTimeline; subtitleCues?: Array<{ start: number; end: number; text: string }> } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!storyboardUrl) {
      setError('缺少查询参数 m2v-storyboard：契约页需要分镜的地址才能建场景。');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(storyboardUrl);
        if (!response.ok) {
          throw new Error(`分镜脚本加载失败: HTTP ${response.status}（${storyboardUrl}）`);
        }
        const input: unknown = await response.json();
        let mediaTimeline: V4MediaTimeline | undefined;
        let subtitleCues: Array<{ start: number; end: number; text: string }> | undefined;
        let source = input;
        if (input && typeof input === 'object' && (input as Record<string, unknown>).version === 4) {
          const effective = { ...(input as Record<string, unknown>) };
          mediaTimeline = effective.mediaTimeline as V4MediaTimeline | undefined;
          subtitleCues = effective.subtitleCues as typeof subtitleCues;
          delete effective.mediaTimeline;
          delete effective.subtitleCues;
          source = effective;
        }
        const parsed = source && typeof source === 'object' && (source as Record<string, unknown>).version === 4
          ? storyboardV4Schema.parse(source)
          : parseStoryboard(source);
        if (!cancelled) {
          setLoaded({ storyboard: parsed, mediaTimeline, subtitleCues });
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storyboardUrl]);

  useEffect(() => {
    const player = playerRef.current;
    if (!loaded || !player) {
      return;
    }
    const storyboard = loaded.mediaTimeline
      ? { ...loaded.storyboard, mediaTimeline: loaded.mediaTimeline } as StoryboardV4 & { mediaTimeline: V4MediaTimeline }
      : loaded.storyboard;
    const contract = createContract({ player, storyboard });
    window.__M2V__ = contract;
    return () => {
      if (window.__M2V__ === contract) {
        delete window.__M2V__;
      }
    };
  }, [loaded]);

  if (error) {
    // 契约未建立时 `__M2V__` 保持未定义：渲染脚本会按「未定义」报错，
    // 这是契约里写明的失败表现，比静默截一张空图有用。
    return (
      <div
        data-m2v-contract-error=""
        style={{
          padding: 40,
          fontFamily: 'monospace',
          fontSize: 22,
          color: '#ff7b72',
          background: '#14161a',
          minHeight: '100vh',
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 16 }}>渲染契约页失败</div>
        <div>{error}</div>
      </div>
    );
  }

  if (!loaded) {
    return <div data-m2v-contract-loading="" style={{ color: '#888', padding: 40 }} />;
  }
  const { storyboard, mediaTimeline, subtitleCues } = loaded;
  const durationInFrames = storyboard.version === 4
    ? resolveStoryboardV4(storyboard, mediaTimeline).totalFrames : totalFrames(storyboard);
  const inputProps = { ...storyboard, ...(mediaTimeline ? { mediaTimeline } : {}), ...(subtitleCues ? { subtitleCues } : {}) };
  const ActiveComposition = storyboard.version === 4 ? M2VCompositionV4 : M2VComposition;

  return (
    <Player
      ref={playerRef}
      component={ActiveComposition as React.ComponentType<Record<string, unknown>>}
      inputProps={inputProps as unknown as Record<string, unknown>}
      durationInFrames={durationInFrames}
      fps={storyboard.fps}
      compositionWidth={storyboard.width}
      compositionHeight={storyboard.height}
      style={{ width: storyboard.width, height: storyboard.height }}
      controls={false}
      clickToPlay={false}
      doubleClickToFullscreen={false}
      allowFullscreen={false}
      acknowledgeRemotionLicense
    />
  );
}

const container = document.getElementById('root');
if (!container) {
  throw new Error('契约页缺少 #root 挂载点');
}

createRoot(container).render(
  <StrictMode>
    <ContractApp />
  </StrictMode>,
);
