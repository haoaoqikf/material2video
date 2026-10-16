/**
 * 素材：把筛选过程压成一段原创示意片段。
 *
 * 片段由 `useMediaAsset('keynote-clip')` 按素材 ID 取用；素材是竖屏（`asset.width` ×
 * `asset.height`），放进横屏画布这一段横向演示区时由作品代码决定裁切方式（cover）。
 * 播放头由旁白时钟驱动而不是自动播放，因此录到帧上的内容是确定的；素材原声不进母版。
 */
import {useEffect, useRef, useState} from 'react';
import {useMediaAsset, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReadyWhen} from './stage';

const STEPS = ['先有多条路径', '按条件缩小范围', '沿选定路线前进'];

export default function Action(props: CodeSceneProps) {
  const assetId = typeof props.props.assetId === 'string' ? props.props.assetId : 'keynote-clip';
  const asset = useMediaAsset(assetId);
  const video = useRef<HTMLVideoElement>(null);
  const [playable, setPlayable] = useState(false);
  const clock = useNarration(props);
  const progress = clock.progress('choice-action-0');
  const seconds = asset.durationSeconds ?? 0;

  // 播放头跟着旁白走：片段是 20 秒的循环示意，取模落在素材时长内。
  useEffect(() => {
    const element = video.current;
    if (!element || !playable || seconds <= 0) return;
    const target = clock.elapsedSeconds % seconds;
    if (Math.abs(element.currentTime - target) > 0.25) element.currentTime = target;
  }, [clock.elapsedSeconds, playable, seconds]);

  useReadyWhen(playable);

  // 素材是竖屏，画布是横屏：片段按 cover 填满一块竖版演示区，两侧留给步骤说明。
  const stage = {left: 130, top: 258, width: 320, height: 520};

  return (
    <Stage props={props} title="从比较走向行动"
      note={`素材实测 ${asset.width}×${asset.height}，画布内裁切由作品决定`}>
      <div style={{position: 'absolute', left: stage.left, top: stage.top, width: stage.width,
        height: stage.height, borderRadius: 18, overflow: 'hidden', border: `2px solid ${COLOR.rule}`,
        background: '#05070a'}}>
        <video ref={video} src={asset.src} muted playsInline preload="auto"
          onLoadedData={() => setPlayable(true)} onError={() => setPlayable(true)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}/>
      </div>
      <div style={{position: 'absolute', left: 520, top: stage.top + 20, width: 1260}}>
        {STEPS.map((label, index) => {
          const threshold = (index + 1) / (STEPS.length + 1);
          const reached = Math.min(1, Math.max(0, (progress - threshold + 0.18) / 0.18));
          return (
            <div key={label} style={{display: 'flex', alignItems: 'center', height: 96, marginBottom: 20,
              padding: '0 26px', borderRadius: 12, background: COLOR.panel,
              border: `2px solid ${reached > 0.5 ? COLOR.accent : COLOR.rule}`,
              opacity: mix(0.4, 1, reached)}}>
              <span style={{width: 56, color: COLOR.accent, fontSize: SIZE.note}}>{`0${index + 1}`}</span>
              <span style={{fontSize: SIZE.lead}}>{label}</span>
            </div>
          );
        })}
        <div style={{marginTop: 18, fontSize: SIZE.body, lineHeight: 1.7, color: COLOR.muted}}>
          这段原创示意只是在复述筛选步骤，不代表某个方案在现实中一定成功。
        </div>
      </div>
      <div style={{position: 'absolute', left: 130, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        先有多条路径，再按条件缩小范围，最后沿选定路线前进
      </div>
    </Stage>
  );
}
