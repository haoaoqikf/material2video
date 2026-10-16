/**
 * 收束：三个自问按旁白推进逐条落下，最后一行给比较设一个终点。
 *
 * 结论不是「少选就好」，而是把目标、必须条件与缺口信息写清楚，再给比较一个截止点。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const ASKS = ['真正的目标是什么', '哪些是必须条件', '还缺哪条关键信息'];

export default function Close(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const progress = clock.progress('choice-close-0');
  const top = 300;
  const rowHeight = 118;

  return (
    <Stage props={props} title="下次犹豫时，先问自己这三个问题"
      note="用它们缩小范围，再给比较设一个合理终点">
      {ASKS.map((label, index) => {
        const reached = Math.min(1, Math.max(0, progress * 3.4 - index * 0.8));
        return (
          <div key={label} style={{position: 'absolute', left: 130, top: top + index * rowHeight,
            width: 1660, height: rowHeight - 22, borderRadius: 14, background: COLOR.panel,
            border: `2px solid ${reached > 0.5 ? COLOR.accent : COLOR.rule}`,
            display: 'flex', alignItems: 'center', padding: '0 34px', opacity: mix(0.35, 1, reached)}}>
            <span style={{width: 64, color: COLOR.accent, fontSize: SIZE.lead}}>{`0${index + 1}`}</span>
            <span style={{fontSize: SIZE.lead}}>{label}</span>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: 130, top: top + 3 * rowHeight + 26, width: 1660,
        display: 'flex', gap: 20}}>
        {['达到足够好就行动', '为新信息留下调整空间'].map((label, index) => (
          <div key={label} style={{padding: '18px 30px', borderRadius: 999, fontSize: SIZE.body,
            border: `2px solid ${COLOR.accent}`, opacity: mix(0.3, 1, progress * 2 - index * 0.5)}}>{label}</div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 130, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        适合的时候开始行动，也为新信息留下调整空间
      </div>
    </Stage>
  );
}
