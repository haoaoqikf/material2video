/**
 * 收束：试之前要设好的三条边界，各自按旁白时间窗点亮。
 *
 * 第一条最硬：涉及健康、安全或不可逆损失时，试错不能绕过专业判断与保护措施。
 * 结尾把有效试错依赖的三件事并排列出，说明高频重复本身不构成方法。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const BOUNDS = [
  {segment: 'darts-bounds-0', title: '定义目标与单次成本', body: '一次最多损失多少，事先写下来；不可逆的损失不进入试验。'},
  {segment: 'darts-bounds-1', title: '一次只改关键变量', body: '保持观察口径一致，否则结果变好也说不清是哪项变化起作用。'},
  {segment: 'darts-bounds-2', title: '设置复盘与停止条件', body: '连续没有收获时先检查假设，必要时换方法或停下来。'},
];
const DEPENDS = ['可承受的成本', '可观察的反馈', '真正的修正'];

export default function Bounds(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const top = 460;
  const height = 260;
  const gap = 28;
  const width = props.width - 2 * INSET;

  return (
    <Stage props={props} title="试之前，先设好边界" lead="边界不是限制尝试，而是让失败停在可承受的范围里">
      {BOUNDS.map((item, index) => {
        const progress = clock.progress(item.segment);
        const y = top + index * (height + gap);
        return (
          <Panel key={item.title} left={INSET} top={y} width={width} height={height}>
            <div style={{position: 'absolute', left: 34, top: 44, right: 34, opacity: mix(0.4, 1, progress)}}>
              <div style={{fontSize: SIZE.lead, fontWeight: 700, marginBottom: 16}}>{item.title}</div>
              <div style={{fontSize: SIZE.body, lineHeight: 1.6, color: COLOR.muted}}>{item.body}</div>
            </div>
            <div style={{position: 'absolute', right: 34, top: 44, width: 90, height: 90, borderRadius: 45,
              border: `3px solid ${COLOR.rule}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: SIZE.note, color: COLOR.accent, opacity: mix(0.4, 1, progress)}}>
              {`0${index + 1}`}
            </div>
          </Panel>
        );
      })}
      <div style={{position: 'absolute', left: INSET, top: top + 3 * (height + gap) + 20,
        display: 'flex', gap: 24}}>
        {DEPENDS.map(item => (
          <div key={item} style={{padding: '16px 26px', borderRadius: 999, border: `2px solid ${COLOR.accent}`,
            fontSize: SIZE.note, color: COLOR.ink}}>{item}</div>
        ))}
      </div>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.body,
        color: COLOR.muted}}>
        有效试错依赖这三件事，高频重复本身并不保证成功
      </div>
    </Stage>
  );
}
